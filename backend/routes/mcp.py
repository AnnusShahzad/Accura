"""
Accura – MCP Server Routes
POST   /api/v1/mcp-servers
GET    /api/v1/mcp-servers
GET    /api/v1/mcp-servers/<id>
PUT    /api/v1/mcp-servers/<id>
DELETE /api/v1/mcp-servers/<id>
POST   /api/v1/mcp-servers/<id>/test
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth, require_tier
from models.mcp_server import MCPServer
from schemas.mcp import CreateMCPServerRequest, UpdateMCPServerRequest
from services.mcp_service import get_accessible_server, list_mcp_tools
from utils.crypto import encrypt
from utils.responses import error, success, validation_error

bp = Blueprint("mcp", url_prefix="/api/v1/mcp-servers")


@bp.post("/")
@require_auth
@require_tier("pro", "business")
async def create_mcp_server(request: Request):
    try:
        body = CreateMCPServerRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])
    server_id = str(uuid.uuid4())

    encrypted_key = ""
    if body.api_key:
        encrypted_key = encrypt(body.api_key)

    await MCPServer.insert(
        MCPServer(
            id=server_id,
            user=user_id,
            name=body.name,
            url=body.url,
            api_key_encrypted=encrypted_key,
            description=body.description,
            transport=body.transport,
            headers=body.headers,
            metadata=body.metadata,
        )
    ).run()

    server = await MCPServer.select().where(MCPServer.id == server_id).first().run()
    server.pop("api_key_encrypted", None)

    return success(server, message="MCP server created", status=201)


@bp.get("/")
@require_auth
async def list_mcp_servers(request: Request):
    user_id = str(request.ctx.user["id"])

    servers = await MCPServer.select().where(
        (MCPServer.user == user_id) | (MCPServer.is_global == True)
    ).order_by(MCPServer.created_at, ascending=False).run()

    # Strip encrypted keys from response
    for s in servers:
        s.pop("api_key_encrypted", None)

    return success(servers)


@bp.get("/<server_id:str>")
@require_auth
async def get_mcp_server(request: Request, server_id: str):
    user_id = str(request.ctx.user["id"])

    server = await MCPServer.select().where(
        (MCPServer.id == server_id)
        & ((MCPServer.user == user_id) | (MCPServer.is_global == True))
    ).first().run()

    if not server:
        return error("MCP server not found", status=404)

    server.pop("api_key_encrypted", None)
    return success(server)


@bp.put("/<server_id:str>")
@require_auth
@require_tier("pro", "business")
async def update_mcp_server(request: Request, server_id: str):
    try:
        body = UpdateMCPServerRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])

    server = await MCPServer.select().where(
        (MCPServer.id == server_id) & (MCPServer.user == user_id)
    ).first().run()
    if not server:
        return error("MCP server not found or not owned by you", status=404)

    updates = body.model_dump(exclude_none=True)

    # Handle API key encryption
    if "api_key" in updates:
        updates["api_key_encrypted"] = encrypt(updates.pop("api_key"))

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await MCPServer.update(updates).where(MCPServer.id == server_id).run()

    updated = await MCPServer.select().where(MCPServer.id == server_id).first().run()
    updated.pop("api_key_encrypted", None)

    return success(updated, message="MCP server updated")


@bp.delete("/<server_id:str>")
@require_auth
async def delete_mcp_server(request: Request, server_id: str):
    user_id = str(request.ctx.user["id"])

    server = await MCPServer.select(MCPServer.id).where(
        (MCPServer.id == server_id) & (MCPServer.user == user_id)
    ).first().run()
    if not server:
        return error("MCP server not found or not owned by you", status=404)

    await MCPServer.delete().where(MCPServer.id == server_id).run()
    return success(message="MCP server deleted")


@bp.post("/<server_id:str>/test")
@require_auth
async def test_mcp_server(request: Request, server_id: str):
    """Test connectivity to an MCP server by listing its tools."""
    server = await get_accessible_server(server_id, str(request.ctx.user["id"]))
    if not server:
        return error("MCP server not found", status=404)
    try:
        tools = await list_mcp_tools(server_id)
    except Exception as exc:
        message = getattr(exc, "message", None) or str(exc)
        return error(f"MCP server test failed: {message}", status=502)
    return success(
        {"tools": [{"name": t.get("name"), "description": t.get("description", "")} for t in tools]},
        message=f"MCP server is reachable ({len(tools)} tools)",
    )
