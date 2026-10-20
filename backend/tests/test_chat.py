"""
Accura – Chat / Conversation Tests
"""

import asyncio

from tests.fakes import FakeAI


async def _wait_done(client, conv_id, headers, timeout=10.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        _, resp = await client.get(f"/api/v1/chat/{conv_id}", headers=headers)
        if resp.json["data"]["status"] != "active":
            return resp.json["data"]
        await asyncio.sleep(0.05)
    raise AssertionError("orchestration did not finish")


async def _create(client, headers, **extra):
    body = {"prompt": "Explain quantum computing in simple terms", **extra}
    _, resp = await client.post("/api/v1/chat", json=body, headers=headers)
    assert resp.status == 201, resp.json
    return resp.json["data"]["id"]


async def test_create_conversation_runs_to_completion(test_client, auth_headers, monkeypatch):
    fake = FakeAI(scores=(90,)).install(monkeypatch)
    conv_id = await _create(test_client, auth_headers)
    conv = await _wait_done(test_client, conv_id, auth_headers)

    assert conv["status"] == "completed"
    assert conv["best_response"] == "Generated answer"
    assert conv["best_score"] == 90
    assert conv["title"] == "Fake Title"
    # metadata comes back as an object, not a JSON string
    assert conv["metadata"]["current_iteration"] == 1
    roles = [m["role"] for m in conv["messages"]]
    assert roles == ["user", "assistant"]
    # One generation + one evaluation, counted once
    assert conv["tokens_input"] == 20 and conv["tokens_output"] == 10
    assert len(fake.calls) == 3  # generate, evaluate, title


async def test_low_scores_trigger_rephrasing(test_client, auth_headers, monkeypatch):
    FakeAI(scores=(40, 50, 95)).install(monkeypatch)
    conv_id = await _create(test_client, auth_headers, threshold=80, max_iterations=5)
    conv = await _wait_done(test_client, conv_id, auth_headers)

    assert [it["score"] for it in conv["iterations"]] == [40, 50, 95]
    assert conv["iterations"][1]["rephrased_prompt"] == "Rephrased prompt"
    assert conv["best_score"] == 95


async def test_provider_failure_marks_conversation_failed(test_client, auth_headers, monkeypatch):
    FakeAI(fail_with="No API key configured for provider 'openai'.").install(monkeypatch)
    conv_id = await _create(test_client, auth_headers)
    conv = await _wait_done(test_client, conv_id, auth_headers)

    assert conv["status"] == "failed"
    assert "No API key" in conv["metadata"]["error"]
    assert conv["title"] == "Explain quantum computing in simple terms"
    assert conv["messages"][-1]["role"] == "system"

    # Fix the "key" and retry
    FakeAI(scores=(88,)).install(monkeypatch)
    _, resp = await test_client.post(f"/api/v1/chat/{conv_id}/retry", headers=auth_headers)
    assert resp.status == 202
    conv = await _wait_done(test_client, conv_id, auth_headers)
    assert conv["status"] == "completed"


async def test_follow_up_sends_history(test_client, auth_headers, monkeypatch):
    fake = FakeAI(delay=0.2).install(monkeypatch)
    conv_id = await _create(test_client, auth_headers)
    await _wait_done(test_client, conv_id, auth_headers)

    _, resp = await test_client.post(
        f"/api/v1/chat/{conv_id}/message", json={"prompt": "And in one sentence?"}, headers=auth_headers
    )
    assert resp.status == 201
    # A second follow-up while busy is rejected instead of racing
    _, busy = await test_client.post(
        f"/api/v1/chat/{conv_id}/message", json={"prompt": "again"}, headers=auth_headers
    )
    assert busy.status == 409
    conv = await _wait_done(test_client, conv_id, auth_headers)

    gen_call = [c for c in fake.calls if c["messages"][-1]["content"] == "And in one sentence?"][0]
    replayed = [m["content"] for m in gen_call["messages"] if m["role"] in ("user", "assistant")]
    assert replayed == ["Explain quantum computing in simple terms", "Generated answer", "And in one sentence?"]
    assert {it["turn"] for it in conv["iterations"]} == {1, 2}


async def test_add_agent_runs_only_new_agent(test_client, auth_headers, monkeypatch):
    fake = FakeAI(scores=(80,)).install(monkeypatch)
    conv_id = await _create(test_client, auth_headers)
    await _wait_done(test_client, conv_id, auth_headers)
    fake.calls.clear()

    _, resp = await test_client.post(
        f"/api/v1/chat/{conv_id}/agent",
        json={"provider": "deepseek", "model": "deepseek-chat"},
        headers=auth_headers,
    )
    assert resp.status == 201
    conv = await _wait_done(test_client, conv_id, auth_headers)
    gen_models = {c["model"] for c in fake.calls if "Evaluate the response" not in c["messages"][-1]["content"]}
    assert gen_models == {"deepseek-chat"}
    assistant = [m for m in conv["messages"] if m["role"] == "assistant"]
    assert len(assistant) == 2 and assistant[1]["metadata"]["alternative"] is True


async def test_list_rename_delete(test_client, auth_headers, monkeypatch):
    FakeAI().install(monkeypatch)
    conv_id = await _create(test_client, auth_headers, title="Mine")
    await _wait_done(test_client, conv_id, auth_headers)

    _, resp = await test_client.get("/api/v1/chat?page=abc", headers=auth_headers)
    assert resp.status == 200
    assert any(c["id"] == conv_id for c in resp.json["data"]["items"])

    _, resp = await test_client.patch(
        f"/api/v1/chat/{conv_id}/rename", json={"title": "Renamed"}, headers=auth_headers
    )
    assert resp.status == 200

    _, resp = await test_client.delete(f"/api/v1/chat/{conv_id}", headers=auth_headers)
    assert resp.status == 200
    _, resp = await test_client.get(f"/api/v1/chat/{conv_id}", headers=auth_headers)
    assert resp.status == 404


async def test_other_users_cannot_see_conversation(test_client, auth_headers, admin_headers, monkeypatch):
    FakeAI().install(monkeypatch)
    conv_id = await _create(test_client, auth_headers)
    _, resp = await test_client.get(f"/api/v1/chat/{conv_id}", headers=admin_headers)
    assert resp.status == 404
    _, resp = await test_client.get("/api/v1/chat/not-a-uuid", headers=auth_headers)
    assert resp.status == 404


async def test_polling_is_not_rate_limited(test_client, auth_headers, monkeypatch):
    FakeAI().install(monkeypatch)
    conv_id = await _create(test_client, auth_headers)
    for _ in range(15):  # basic tier allows 10 generation requests / minute
        _, resp = await test_client.get(f"/api/v1/chat/{conv_id}", headers=auth_headers)
        assert resp.status == 200



async def test_status_flips_only_after_answer_and_title_exist(test_client, auth_headers, monkeypatch):
    """Clients stop polling when status leaves 'active', so the answer and
    the auto-title must already be stored when the status flips."""
    from models.chat import ChatMessage, Conversation

    snapshot = {}
    real_update = Conversation.update

    class CheckedQuery:
        def __init__(self, query):
            self.query = query

        def where(self, *args):
            self.query = self.query.where(*args)
            return self

        async def run(self):
            conv_id = snapshot["id"]
            snapshot["assistant_msgs"] = await ChatMessage.count().where(
                (ChatMessage.conversation == conv_id) & (ChatMessage.role == "assistant")
            ).run()
            row = await Conversation.select(Conversation.title).where(Conversation.id == conv_id).first().run()
            snapshot["title"] = row["title"]
            return await self.query.run()

    def spy(values=None, *a, **kw):
        query = real_update(values, *a, **kw)
        if values and values.get(Conversation.status) == "completed":
            return CheckedQuery(query)
        return query

    FakeAI(delay=0.05).install(monkeypatch)
    monkeypatch.setattr(Conversation, "update", spy)
    _, resp = await test_client.post("/api/v1/chat", json={"prompt": "Order check"}, headers=auth_headers)
    snapshot["id"] = resp.json["data"]["id"]
    conv = await _wait_done(test_client, snapshot["id"], auth_headers)

    assert conv["status"] == "completed"
    assert snapshot == {"id": snapshot["id"], "assistant_msgs": 1, "title": "Fake Title"}


async def test_omitted_provider_uses_server_default(test_client, auth_headers, monkeypatch):
    from config import settings as cfg

    monkeypatch.setitem(cfg._data["ai"], "default_provider", "custom")
    fake = FakeAI().install(monkeypatch)
    _, resp = await test_client.post("/api/v1/chat", json={"prompt": "hi", "generator_model": "m"},
                                     headers=auth_headers)
    conv = await _wait_done(test_client, resp.json["data"]["id"], auth_headers)
    assert {a["provider"] for a in conv["agents"]} == {"custom"}
    assert {c["provider"] for c in fake.calls} == {"custom"}
