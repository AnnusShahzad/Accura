"""
Accura – MCP (Model Context Protocol) Service
Handles calling user-configured and global MCP servers.
"""

from __future__ import annotations

import logging

import httpx

from models.mcp_server import MCPServer
from utils.crypto import decrypt
from utils.exceptions import MCPServerError

logger = logging.getLogger("accura.mcp_service")


async def get_user_mcp_servers(user_id: str) -> list[dict]:
    """Return all active MCP servers for a user (user-level + global)."""
    servers = await MCPServer.select().where(
        ((MCPServer.user == user_id) | (MCPServer.is_global == True))
        & (MCPServer.is_active == True)
    ).run()
    return servers


async def call_mcp_server(
    server_id: str,
    method: str,
    params: dict | None = None,
    timeout: int = 30,
) -> dict:
    """Invoke a tool/method on an MCP server via HTTP/SSE transport."""

    server = await MCPServer.select().where(MCPServer.id == server_id).first().run()
    if not server:
        raise MCPServerError("MCP server not found")

    if not server["is_active"]:
        raise MCPServerError("MCP server is inactive")

    # Build request
    headers = dict(server.get("headers", {}))
    if server["api_key_encrypted"]:
        try:
            api_key = decrypt(server["api_key_encrypted"])
            headers["Authorization"] = f"Bearer {api_key}"
        except Exception:
            logger.warning("Failed to decrypt MCP server API key for server %s", server_id)

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(server["url"], json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()
    except httpx.TimeoutException:
        raise MCPServerError(f"MCP server '{server['name']}' timed out")
    except Exception as exc:
        logger.exception("MCP server call failed: %s", server["name"])
        raise MCPServerError(f"MCP server error: {exc}")

    if "error" in result:
        raise MCPServerError(f"MCP server returned error: {result['error']}")

    return result.get("result", {})


async def list_mcp_tools(server_id: str) -> list[dict]:
    """List available tools on an MCP server."""
    return await call_mcp_server(server_id, "tools/list")
