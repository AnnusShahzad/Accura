"""
Accura – MCP integration tests against an in-process fake MCP server.
"""

import asyncio
import json

import httpx

import services.mcp_service as mcp_service
from tests.conftest import register_and_login
from tests.fakes import FakeAI
from tests.test_chat import _wait_done


def _fake_mcp_server(log: list):
    """Streamable HTTP MCP server with one 'get_weather' tool. Replies to
    tools/call over SSE to exercise both response encodings."""

    def handler(request: httpx.Request) -> httpx.Response:
        msg = json.loads(request.content)
        log.append(msg.get("method"))
        if "id" not in msg:  # notification
            return httpx.Response(202)
        if request.headers.get("authorization") != "Bearer secret-token":
            return httpx.Response(401)
        method = msg["method"]
        if method == "initialize":
            result = {"protocolVersion": mcp_service.PROTOCOL_VERSION, "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fake", "version": "1"}}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": msg["id"], "result": result},
                                  headers={"Mcp-Session-Id": "sess-1"})
        assert request.headers.get("mcp-session-id") == "sess-1"
        if method == "tools/list":
            result = {"tools": [{"name": "get_weather", "description": "Weather by city",
                                 "inputSchema": {"type": "object",
                                                 "properties": {"city": {"type": "string"}}}}]}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": msg["id"], "result": result})
        if method == "tools/call":
            city = msg["params"]["arguments"]["city"]
            body = {"jsonrpc": "2.0", "id": msg["id"],
                    "result": {"content": [{"type": "text", "text": f"Sunny in {city}"}]}}
            return httpx.Response(200, text=f"event: message\ndata: {json.dumps(body)}\n\n",
                                  headers={"Content-Type": "text/event-stream"})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": msg["id"],
                                         "error": {"code": -32601, "message": "nope"}})

    return httpx.MockTransport(handler)


async def test_mcp_server_requires_pro(test_client, auth_headers):
    _, resp = await test_client.post("/api/v1/mcp-servers", json={
        "name": "x", "url": "https://mcp.example.com/mcp",
    }, headers=auth_headers)
    assert resp.status == 403


async def test_mcp_tools_are_listed_and_called(test_client, sample_user, monkeypatch):
    log: list = []
    transport = _fake_mcp_server(log)
    monkeypatch.setattr(
        mcp_service, "_client_factory",
        lambda **kw: httpx.AsyncClient(transport=transport, **kw),
    )
    headers = await register_and_login(test_client, sample_user, tier="pro")

    _, resp = await test_client.post("/api/v1/mcp-servers", json={
        "name": "Weather", "url": "https://mcp.example.com/mcp", "api_key": "secret-token",
        "headers": {"X-Extra": "1"},
    }, headers=headers)
    assert resp.status == 201, resp.json
    server = resp.json["data"]
    assert server["transport"] == "http"
    assert server["headers"] == {"X-Extra": "1"}
    assert "api_key_encrypted" not in server

    _, resp = await test_client.post(f"/api/v1/mcp-servers/{server['id']}/test", headers=headers)
    assert resp.status == 200, resp.json
    assert resp.json["data"]["tools"][0]["name"] == "get_weather"

    fake = FakeAI(tool_call={"id": "call_1", "name": "mcp0_get_weather",
                             "arguments": json.dumps({"city": "Lahore"})}).install(monkeypatch)
    _, resp = await test_client.post("/api/v1/chat", json={"prompt": "Weather in Lahore?"}, headers=headers)
    conv = await _wait_done(test_client, resp.json["data"]["id"], headers)

    assert conv["status"] == "completed", conv.get("metadata")
    assert conv["best_response"] == "Generated answer [Sunny in Lahore]"
    assert "tools/call" in log
    gen_with_tools = [c for c in fake.calls if c.get("tools")]
    assert gen_with_tools[0]["tools"][0]["function"]["name"] == "mcp0_get_weather"


async def test_unreachable_mcp_server_does_not_break_chat(test_client, sample_user, monkeypatch):
    def refuse(request):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(
        mcp_service, "_client_factory",
        lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(refuse), **kw),
    )
    headers = await register_and_login(test_client, sample_user, tier="pro")
    _, resp = await test_client.post("/api/v1/mcp-servers", json={
        "name": "Down", "url": "https://down.example.com/mcp",
    }, headers=headers)
    server_id = resp.json["data"]["id"]

    _, resp = await test_client.post(f"/api/v1/mcp-servers/{server_id}/test", headers=headers)
    assert resp.status == 502
    assert "Could not reach" in resp.json["message"]

    FakeAI().install(monkeypatch)
    _, resp = await test_client.post("/api/v1/chat", json={"prompt": "hi"}, headers=headers)
    conv = await _wait_done(test_client, resp.json["data"]["id"], headers)
    assert conv["status"] == "completed"
    await asyncio.sleep(0)
