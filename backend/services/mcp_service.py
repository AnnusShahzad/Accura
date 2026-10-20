"""
Accura – MCP (Model Context Protocol) Service
Handles calling user-configured and global MCP servers.

Implements the client side of the two network transports from the MCP
spec – just enough to discover and call tools:

  * ``http`` – Streamable HTTP: JSON-RPC POSTed to one endpoint, answered
    with either a JSON body or a short ``text/event-stream``.
  * ``sse``  – legacy HTTP+SSE: a GET stream announces a POST endpoint via
    an ``endpoint`` event; replies arrive back on the stream.

Every operation opens its own short-lived session (initialize → request),
which keeps the generator stateless at the cost of one extra round trip.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import urljoin

import httpx

from models.mcp_server import MCPServer
from utils.crypto import decrypt
from utils.exceptions import MCPServerError
from utils.url_guard import UnsafeURLError, ensure_public_url, private_urls_allowed

logger = logging.getLogger("accura.mcp_service")

PROTOCOL_VERSION = "2025-06-18"

# Indirection so tests can substitute an in-process transport.
_client_factory = httpx.AsyncClient
_CLIENT_INFO = {"name": "accura", "version": "1.0.0"}


async def get_user_mcp_servers(user_id: str) -> list[dict]:
    """Return all active MCP servers for a user (user-level + global)."""
    servers = await MCPServer.select().where(
        ((MCPServer.user == user_id) | (MCPServer.is_global == True))  # noqa: E712
        & (MCPServer.is_active == True)  # noqa: E712
    ).run()
    return servers


async def get_accessible_server(server_id: str, user_id: str) -> dict | None:
    """Return the server if *user_id* owns it or it is global."""
    return await MCPServer.select().where(
        (MCPServer.id == server_id)
        & ((MCPServer.user == user_id) | (MCPServer.is_global == True))  # noqa: E712
    ).first().run()


def _headers_for(server: dict) -> dict[str, str]:
    headers = {str(k): str(v) for k, v in (server.get("headers") or {}).items()}
    if server.get("api_key_encrypted"):
        try:
            headers["Authorization"] = f"Bearer {decrypt(server['api_key_encrypted'])}"
        except Exception:
            logger.warning("Failed to decrypt MCP server API key for server %s", server["id"])
    return headers


def _iter_sse(lines: list[str]) -> list[tuple[str, str]]:
    """Parse already-buffered SSE lines into (event, data) tuples."""
    events: list[tuple[str, str]] = []
    event, data = "message", []
    for line in lines + [""]:
        if not line:
            if data:
                events.append((event, "\n".join(data)))
            event, data = "message", []
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
    return events


def _unwrap(message: dict, server_name: str) -> Any:
    if "error" in message:
        err = message["error"]
        detail = err.get("message", err) if isinstance(err, dict) else err
        raise MCPServerError(f"MCP server '{server_name}' returned an error: {detail}")
    return message.get("result", {})


class _Session:
    """Base class: request/notify over one transport."""

    def __init__(self, server: dict, client: httpx.AsyncClient):
        self.server = server
        self.client = client
        self._next_id = 1

    def _rpc(self, method: str, params: dict | None) -> dict:
        msg = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        self._next_id += 1
        return msg

    async def request(self, method: str, params: dict | None = None) -> Any:  # pragma: no cover
        raise NotImplementedError

    async def notify(self, method: str, params: dict | None = None) -> None:  # pragma: no cover
        raise NotImplementedError

    async def initialize(self) -> None:
        await self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": _CLIENT_INFO,
        })
        await self.notify("notifications/initialized")


class _StreamableHTTPSession(_Session):
    def __init__(self, server: dict, client: httpx.AsyncClient):
        super().__init__(server, client)
        self.session_id: str | None = None
        self.protocol_version: str | None = None

    def _headers(self) -> dict[str, str]:
        headers = {
            **_headers_for(self.server),
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        return headers

    async def _post(self, payload: dict) -> httpx.Response:
        resp = await self.client.post(self.server["url"], json=payload, headers=self._headers())
        if resp.status_code >= 400:
            raise MCPServerError(
                f"MCP server '{self.server['name']}' answered HTTP {resp.status_code}"
            )
        if resp.headers.get("mcp-session-id"):
            self.session_id = resp.headers["mcp-session-id"]
        return resp

    async def request(self, method: str, params: dict | None = None) -> Any:
        payload = self._rpc(method, params)
        resp = await self._post(payload)
        ctype = resp.headers.get("content-type", "")
        if "text/event-stream" in ctype:
            for _, data in _iter_sse(resp.text.splitlines()):
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if msg.get("id") == payload["id"]:
                    result = _unwrap(msg, self.server["name"])
                    break
            else:
                raise MCPServerError(f"MCP server '{self.server['name']}' sent no response")
        else:
            try:
                result = _unwrap(resp.json(), self.server["name"])
            except (json.JSONDecodeError, ValueError):
                raise MCPServerError(f"MCP server '{self.server['name']}' sent invalid JSON")
        if method == "initialize" and isinstance(result, dict):
            self.protocol_version = result.get("protocolVersion")
        return result

    async def notify(self, method: str, params: dict | None = None) -> None:
        await self._post({"jsonrpc": "2.0", "method": method, "params": params or {}})


class _LegacySSESession(_Session):
    def __init__(self, server: dict, client: httpx.AsyncClient, stream: httpx.Response):
        super().__init__(server, client)
        self.stream = stream
        self.lines = stream.aiter_lines()
        self.endpoint: str | None = None

    async def _next_event(self) -> tuple[str, str]:
        event, data = "message", []
        async for line in self.lines:
            line = line.rstrip("\r")
            if not line:
                if data:
                    return event, "\n".join(data)
                event = "message"
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())
        raise MCPServerError(f"MCP server '{self.server['name']}' closed the event stream")

    async def connect(self) -> None:
        while self.endpoint is None:
            event, data = await self._next_event()
            if event == "endpoint":
                endpoint = urljoin(self.server["url"], data.strip())
                # The server chooses where we POST; hold it to the same rule
                try:
                    await ensure_public_url(endpoint, what="MCP endpoint")
                except UnsafeURLError as exc:
                    raise MCPServerError(str(exc))
                self.endpoint = endpoint

    async def _post(self, payload: dict) -> None:
        resp = await self.client.post(
            self.endpoint,
            json=payload,
            headers={**_headers_for(self.server), "Content-Type": "application/json"},
        )
        if resp.status_code >= 400:
            raise MCPServerError(
                f"MCP server '{self.server['name']}' answered HTTP {resp.status_code}"
            )

    async def request(self, method: str, params: dict | None = None) -> Any:
        payload = self._rpc(method, params)
        await self._post(payload)
        while True:
            _, data = await self._next_event()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == payload["id"]:
                return _unwrap(msg, self.server["name"])

    async def notify(self, method: str, params: dict | None = None) -> None:
        await self._post({"jsonrpc": "2.0", "method": method, "params": params or {}})


@asynccontextmanager
async def _open_session(server: dict, timeout: int) -> AsyncIterator[_Session]:
    transport = (server.get("transport") or "http").lower()
    if transport == "stdio":
        raise MCPServerError(
            "stdio MCP servers can't be reached over the network; "
            "expose the server over HTTP (Streamable HTTP or SSE) instead"
        )
    try:
        await ensure_public_url(server["url"], what="MCP server URL")
    except UnsafeURLError as exc:
        raise MCPServerError(str(exc))
    try:
        # A redirect could bounce a vetted public URL to a private one
        follow = private_urls_allowed()
        async with _client_factory(timeout=timeout, follow_redirects=follow) as client:
            if transport == "sse":
                async with client.stream(
                    "GET",
                    server["url"],
                    headers={**_headers_for(server), "Accept": "text/event-stream"},
                ) as stream:
                    if stream.status_code >= 400:
                        raise MCPServerError(
                            f"MCP server '{server['name']}' answered HTTP {stream.status_code}"
                        )
                    session = _LegacySSESession(server, client, stream)
                    await session.connect()
                    await session.initialize()
                    yield session
            else:
                session = _StreamableHTTPSession(server, client)
                await session.initialize()
                yield session
    except MCPServerError:
        raise
    except httpx.TimeoutException:
        raise MCPServerError(f"MCP server '{server['name']}' timed out")
    except httpx.HTTPError as exc:
        raise MCPServerError(f"Could not reach MCP server '{server['name']}': {exc}")


async def _load_server(server_id: str) -> dict:
    server = await MCPServer.select().where(MCPServer.id == server_id).first().run()
    if not server:
        raise MCPServerError("MCP server not found")
    if not server["is_active"]:
        raise MCPServerError("MCP server is inactive")
    return server


async def list_mcp_tools(server_id: str, timeout: int = 30) -> list[dict]:
    """List available tools on an MCP server."""
    server = await _load_server(server_id)
    async with _open_session(server, timeout) as session:
        result = await session.request("tools/list")
    return list(result.get("tools", [])) if isinstance(result, dict) else []


async def call_mcp_tool(server_id: str, name: str, arguments: dict, timeout: int = 60) -> str:
    """Call a tool and return its result flattened to text for the model."""
    server = await _load_server(server_id)
    async with _open_session(server, timeout) as session:
        result = await session.request("tools/call", {"name": name, "arguments": arguments})
    return tool_result_to_text(result)


def tool_result_to_text(result: Any) -> str:
    if not isinstance(result, dict):
        return json.dumps(result, default=str)
    parts: list[str] = []
    for item in result.get("content", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            parts.append(str(item.get("text", "")))
        elif item.get("type") == "resource":
            res = item.get("resource", {})
            parts.append(str(res.get("text") or res.get("uri", "")))
        else:
            parts.append(f"[{item.get('type', 'content')} omitted]")
    if not parts and result.get("structuredContent") is not None:
        parts.append(json.dumps(result["structuredContent"], default=str))
    text = "\n".join(p for p in parts if p)
    if result.get("isError"):
        text = f"Tool error: {text}"
    return text or "(no output)"


async def discover_tools(servers: list[dict], timeout: int = 20) -> list[dict]:
    """Collect tools from several servers as OpenAI function specs.

    Each entry: {"server_id", "tool_name", "spec"}. Servers that fail are
    skipped (and logged) so one broken server doesn't block generation.
    """
    discovered: list[dict] = []
    for server in servers:
        try:
            tools = await list_mcp_tools(str(server["id"]), timeout=timeout)
        except Exception as exc:
            logger.warning("Skipping MCP server %s: %s", server.get("name"), exc)
            continue
        for tool in tools:
            name = tool.get("name")
            if not name:
                continue
            # Function names must be unique and match ^[a-zA-Z0-9_-]{1,64}$
            fn_name = f"mcp{len(discovered)}_{name}"
            fn_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in fn_name)[:64]
            discovered.append({
                "server_id": str(server["id"]),
                "tool_name": name,
                "spec": {
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "description": (tool.get("description") or "")[:1024]
                        + f" (via MCP server '{server.get('name')}')",
                        "parameters": tool.get("inputSchema") or {"type": "object", "properties": {}},
                    },
                },
            })
    return discovered
