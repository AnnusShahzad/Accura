"""
Accura – Tests for the outbound integrations: the OpenAI-compatible AI
client, BYOK key handling, web search and Slack/Teams webhooks. Every
external HTTP call goes to an in-process httpx.MockTransport.
"""

import json

import httpx
import pytest

import services.ai_client as ai_client
import services.search_service as search_service
import utils.webhooks as webhooks
from config import settings
from models.user import User
from utils.exceptions import AIProviderError


def _completion(content="hi", tool_calls=None):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": "c1", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


@pytest.fixture
def fake_provider(monkeypatch):
    """Route AsyncOpenAI through a mock transport; returns the request log."""
    calls = []
    behaviour = {"handler": lambda body: httpx.Response(200, json=_completion())}

    def handler(request):
        body = json.loads(request.content)
        calls.append({"url": str(request.url), "auth": request.headers.get("authorization"), "body": body})
        return behaviour["handler"](body)

    real = ai_client.AsyncOpenAI

    def factory(**kwargs):
        return real(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), **kwargs)

    monkeypatch.setattr(ai_client, "AsyncOpenAI", factory)
    monkeypatch.setitem(settings._data["ai"]["providers"]["openai"], "api_key", "sk-platform")
    return calls, behaviour


async def test_platform_key_and_plain_model_params(fake_provider):
    calls, _ = fake_provider
    result = await ai_client.chat_completion(None, "openai", "gpt-4o", [{"role": "user", "content": "x"}])
    assert result["content"] == "hi" and result["usage"]["total_tokens"] == 5
    body = calls[0]["body"]
    assert calls[0]["auth"] == "Bearer sk-platform"
    assert body["max_tokens"] == 4096 and body["temperature"] == 0.7


async def test_reasoning_models_get_max_completion_tokens(fake_provider):
    calls, _ = fake_provider
    await ai_client.chat_completion(None, "openai", "gpt-5.2", [{"role": "user", "content": "x"}])
    body = calls[0]["body"]
    assert "max_tokens" not in body and "temperature" not in body
    assert body["max_completion_tokens"] == 4096


async def test_retries_without_rejected_temperature(fake_provider):
    calls, behaviour = fake_provider

    def handler(body):
        if "temperature" in body:
            return httpx.Response(400, json={"error": {"message": "Unsupported value: 'temperature'"}})
        return httpx.Response(200, json=_completion("ok"))

    behaviour["handler"] = handler
    result = await ai_client.chat_completion(None, "openai", "some-model", [{"role": "user", "content": "x"}])
    assert result["content"] == "ok"
    assert len(calls) == 2 and "temperature" not in calls[1]["body"]


async def test_provider_errors_become_readable(fake_provider):
    _, behaviour = fake_provider
    behaviour["handler"] = lambda body: httpx.Response(401, json={"error": {"message": "bad key"}})
    with pytest.raises(AIProviderError) as exc:
        await ai_client.chat_completion(None, "openai", "gpt-4o", [{"role": "user", "content": "x"}])
    assert "rejected the API key" in exc.value.message


async def test_missing_key_is_actionable(monkeypatch):
    monkeypatch.setitem(settings._data["ai"]["providers"]["deepseek"], "api_key", "")
    with pytest.raises(AIProviderError) as exc:
        await ai_client.chat_completion(None, "deepseek", "deepseek-chat", [{"role": "user", "content": "x"}])
    assert "Settings → API Keys" in exc.value.message


async def test_tool_calls_are_returned(fake_provider):
    _, behaviour = fake_provider
    tc = [{"id": "t1", "type": "function", "function": {"name": "f", "arguments": "{\"a\": 1}"}}]
    behaviour["handler"] = lambda body: httpx.Response(200, json=_completion("", tc))
    result = await ai_client.chat_completion(
        None, "openai", "gpt-4o", [{"role": "user", "content": "x"}],
        tools=[{"type": "function", "function": {"name": "f", "parameters": {"type": "object"}}}],
    )
    assert result["tool_calls"] == [{"id": "t1", "name": "f", "arguments": "{\"a\": 1}"}]


async def test_byok_keys_crud_and_use(test_client, auth_headers, fake_provider):
    calls, _ = fake_provider

    _, resp = await test_client.post("/api/v1/api-keys", json={
        "provider": "custom", "api_key": "sk-mine-1234567890",
    }, headers=auth_headers)
    assert resp.status == 422  # custom needs a base URL

    _, resp = await test_client.post("/api/v1/api-keys", json={
        "provider": "custom", "label": "Mine", "api_key": " sk-mine-1234567890 ",
        "base_url": "https://llm.example.com/v1",
    }, headers=auth_headers)
    assert resp.status == 201
    key_id = resp.json["data"]["id"]
    assert resp.json["data"]["key_preview"] == "sk-m...7890"

    _, resp = await test_client.get("/api/v1/api-keys", headers=auth_headers)
    assert [k["key_preview"] for k in resp.json["data"]] == ["sk-m...7890"]

    _, me = await test_client.get("/api/v1/user/me", headers=auth_headers)
    user_id = me.json["data"]["user"]["id"]
    await ai_client.chat_completion(user_id, "custom", "my-model", [{"role": "user", "content": "x"}])
    assert calls[-1]["auth"] == "Bearer sk-mine-1234567890"  # trimmed, decrypted
    assert calls[-1]["url"].startswith("https://llm.example.com/v1/")

    _, resp = await test_client.put(f"/api/v1/api-keys/{key_id}", json={"is_active": False},
                                    headers=auth_headers)
    assert resp.status == 200
    with pytest.raises(AIProviderError):  # inactive key, no platform key for custom
        await ai_client.chat_completion(user_id, "custom", "my-model", [{"role": "user", "content": "x"}])

    _, resp = await test_client.delete(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
    assert resp.status == 200
    _, resp = await test_client.delete(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
    assert resp.status == 404


@pytest.fixture
def mock_http(monkeypatch):
    """Patch httpx.AsyncClient in a module with a recording mock transport."""
    real = httpx.AsyncClient  # captured once, so re-installing replaces the handler

    def install(module, handler):
        seen = []

        def record(request):
            seen.append(request)
            return handler(request)

        class Client(real):
            def __init__(self, *a, **kw):
                kw["transport"] = httpx.MockTransport(record)
                super().__init__(*a, **kw)

        monkeypatch.setattr(module.httpx, "AsyncClient", Client)
        return seen
    return install


async def test_search_unconfigured_returns_nothing(monkeypatch):
    monkeypatch.setitem(settings._data["search"], "google_api_key", "")
    assert await search_service.google_search("anything") == []


async def test_search_filters_domains(monkeypatch, mock_http, admin_headers, test_client):
    monkeypatch.setitem(settings._data["search"], "google_api_key", "k")
    monkeypatch.setitem(settings._data["search"], "google_cse_id", "cx")
    await test_client.post("/api/v1/admin/domain-rules", json={
        "domain": "spam.example", "rule_type": "blacklist",
    }, headers=admin_headers)
    items = [
        {"title": "Good", "snippet": "s", "link": "https://docs.python.org/3/"},
        {"title": "Bad", "snippet": "s", "link": "https://www.spam.example/x"},
    ]
    seen = mock_http(search_service, lambda r: httpx.Response(200, json={"items": items}))
    results = await search_service.google_search("python docs", num_results=5, date_restrict="m3")
    assert [r["title"] for r in results] == ["Good"]
    assert seen[0].url.params["dateRestrict"] == "m3"

    mock_http(search_service, lambda r: httpx.Response(500))
    assert await search_service.google_search("python docs") == []


async def test_webhooks(mock_http):
    seen = mock_http(webhooks, lambda r: httpx.Response(200))
    assert await webhooks.send_slack_notification("https://hooks.slack.test/x", "hello")
    assert await webhooks.send_teams_notification("https://teams.test/x", "Title", "Body")
    assert json.loads(seen[0].content) == {"text": "hello"}
    assert json.loads(seen[1].content)["title"] == "Title"

    mock_http(webhooks, lambda r: httpx.Response(500))
    assert not await webhooks.send_slack_notification("https://hooks.slack.test/x", "hello")


async def test_notifications_api(test_client, auth_headers):
    from services.notification_service import send_notification

    _, me = await test_client.get("/api/v1/user/me", headers=auth_headers)
    user_id = me.json["data"]["user"]["id"]
    assert await send_notification(user_id, "T", "B") == ["in_app"]

    _, resp = await test_client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.json["data"]["count"] == 1
    _, resp = await test_client.get("/api/v1/notifications", headers=auth_headers)
    note = resp.json["data"][0]
    assert note["metadata"] == {}

    _, resp = await test_client.patch(f"/api/v1/notifications/{note['id']}/read", headers=auth_headers)
    _, resp = await test_client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.json["data"]["count"] == 0
    _, resp = await test_client.delete(f"/api/v1/notifications/{note['id']}", headers=auth_headers)
    assert resp.status == 200
    _, resp = await test_client.delete(f"/api/v1/notifications/{note['id']}", headers=auth_headers)
    assert resp.status == 404

    await User.select(User.id).where(User.id == user_id).first().run()
