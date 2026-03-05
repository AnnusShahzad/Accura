"""
Accura – Admin Routes
All routes require admin authentication.

GET    /api/v1/admin/dashboard
GET    /api/v1/admin/users
GET    /api/v1/admin/users/<id>
PUT    /api/v1/admin/users/<id>
GET    /api/v1/admin/config
PUT    /api/v1/admin/config
GET    /api/v1/admin/system-prompts
PUT    /api/v1/admin/system-prompts
GET    /api/v1/admin/domain-rules
POST   /api/v1/admin/domain-rules
DELETE /api/v1/admin/domain-rules/<id>
GET    /api/v1/admin/plans
PUT    /api/v1/admin/plans/<id>
POST   /api/v1/admin/mcp-servers
GET    /api/v1/admin/mcp-servers
PUT    /api/v1/admin/mcp-servers/<id>
DELETE /api/v1/admin/mcp-servers/<id>
GET    /api/v1/admin/contact-requests
PUT    /api/v1/admin/contact-requests/<id>
POST   /api/v1/admin/reload-config
"""

from __future__ import annotations

import uuid

from sanic import Blueprint, Request

from middleware.auth_middleware import require_admin, require_auth
from models.admin import AdminConfig, DomainRule, SystemPrompt
from models.chat import Conversation, Iteration
from models.contact import ContactRequest
from models.mcp_server import MCPServer
from models.subscription import Subscription, SubscriptionPlan, Transaction
from models.user import User
from schemas.admin import (
    AdminConfigUpdateRequest,
    AdminUserUpdateRequest,
    DomainRuleRequest,
    PlanUpdateRequest,
    SystemPromptUpdateRequest,
)
from services.billing_service import get_revenue_summary
from utils.crypto import encrypt
from utils.responses import error, paginated, success

bp = Blueprint("admin", url_prefix="/api/v1/admin")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@bp.get("/dashboard")
@require_auth
@require_admin
async def dashboard(request: Request):
    total_users = await User.count().run()
    active_subs = await Subscription.count().where(Subscription.status == "active").run()

    revenue = await get_revenue_summary()

    # Tier distribution
    basic = await User.count().where(User.tier == "basic").run()
    pro = await User.count().where(User.tier == "pro").run()
    business = await User.count().where(User.tier == "business").run()

    # Recent transactions
    recent_txns = await Transaction.select().order_by(
        Transaction.created_at, ascending=False
    ).limit(20).run()

    return success({
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "total_revenue": revenue["total_revenue"],
        "tier_distribution": {"basic": basic, "pro": pro, "business": business},
        "recent_transactions": recent_txns,
    })


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@bp.get("/users")
@require_auth
@require_admin
async def list_users(request: Request):
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    offset = (page - 1) * per_page

    search = request.args.get("search", "")

    query = User.select(
        User.id, User.email, User.username, User.tier,
        User.is_active, User.is_verified, User.is_admin, User.created_at,
    )
    if search:
        query = query.where(
            (User.email.like(f"%{search}%")) | (User.username.like(f"%{search}%"))
        )

    total = await User.count().run()
    users = await query.order_by(User.created_at, ascending=False).limit(per_page).offset(offset).run()

    return paginated(users, total, page, per_page)


@bp.get("/users/<user_id:str>")
@require_auth
@require_admin
async def get_user(request: Request, user_id: str):
    user = await User.select().where(User.id == user_id).first().run()
    if not user:
        return error("User not found", status=404)
    user.pop("hashed_password", None)
    return success(user)


@bp.put("/users/<user_id:str>")
@require_auth
@require_admin
async def update_user(request: Request, user_id: str):
    try:
        body = AdminUserUpdateRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error("No fields to update", status=422)

    await User.update(updates).where(User.id == user_id).run()
    return success(message="User updated")


# ---------------------------------------------------------------------------
# Admin Config (key-value store)
# ---------------------------------------------------------------------------

@bp.get("/config")
@require_auth
@require_admin
async def list_config(request: Request):
    configs = await AdminConfig.select().order_by(AdminConfig.key).run()
    return success(configs)


@bp.put("/config")
@require_auth
@require_admin
async def upsert_config(request: Request):
    try:
        body = AdminConfigUpdateRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    existing = await AdminConfig.select().where(AdminConfig.key == body.key).first().run()
    if existing:
        await AdminConfig.update({
            AdminConfig.value: body.value,
            AdminConfig.description: body.description,
            AdminConfig.updated_by: request.ctx.user["email"],
        }).where(AdminConfig.key == body.key).run()
    else:
        await AdminConfig.insert(
            AdminConfig(
                id=str(uuid.uuid4()),
                key=body.key,
                value=body.value,
                description=body.description,
                updated_by=request.ctx.user["email"],
            )
        ).run()

    return success(message="Config updated")


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

@bp.get("/system-prompts")
@require_auth
@require_admin
async def list_system_prompts(request: Request):
    prompts = await SystemPrompt.select().run()
    return success(prompts)


@bp.post("/system-prompts")
@require_auth
@require_admin
async def create_system_prompt(request: Request):
    try:
        body = SystemPromptUpdateRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    # Check if role already exists
    existing = await SystemPrompt.select().where(SystemPrompt.role == body.role).first().run()
    if existing:
        return error(f"System prompt for role '{body.role}' already exists. Use PUT to update.", status=409)

    prompt_id = str(uuid.uuid4())
    await SystemPrompt.insert(
        SystemPrompt(
            id=prompt_id,
            role=body.role,
            prompt=body.prompt,
            version=body.version,
        )
    ).run()

    created = await SystemPrompt.select().where(SystemPrompt.id == prompt_id).first().run()
    return success(created, message="System prompt created", status=201)


@bp.put("/system-prompts")
@require_auth
@require_admin
async def upsert_system_prompt(request: Request):
    try:
        body = SystemPromptUpdateRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    existing = await SystemPrompt.select().where(SystemPrompt.role == body.role).first().run()
    if existing:
        await SystemPrompt.update({
            SystemPrompt.prompt: body.prompt,
            SystemPrompt.version: body.version,
        }).where(SystemPrompt.role == body.role).run()
    else:
        await SystemPrompt.insert(
            SystemPrompt(
                id=str(uuid.uuid4()),
                role=body.role,
                prompt=body.prompt,
                version=body.version,
            )
        ).run()

    return success(message="System prompt updated")


@bp.put("/system-prompts/<prompt_id:str>")
@require_auth
@require_admin
async def update_system_prompt_by_id(request: Request, prompt_id: str):
    try:
        body = SystemPromptUpdateRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    existing = await SystemPrompt.select().where(SystemPrompt.id == prompt_id).first().run()
    if not existing:
        return error("System prompt not found", status=404)

    await SystemPrompt.update({
        SystemPrompt.role: body.role,
        SystemPrompt.prompt: body.prompt,
        SystemPrompt.version: body.version,
    }).where(SystemPrompt.id == prompt_id).run()

    updated = await SystemPrompt.select().where(SystemPrompt.id == prompt_id).first().run()
    return success(updated, message="System prompt updated")


@bp.delete("/system-prompts/<prompt_id:str>")
@require_auth
@require_admin
async def delete_system_prompt(request: Request, prompt_id: str):
    existing = await SystemPrompt.select().where(SystemPrompt.id == prompt_id).first().run()
    if not existing:
        return error("System prompt not found", status=404)
    await SystemPrompt.delete().where(SystemPrompt.id == prompt_id).run()
    return success(message="System prompt deleted")


# ---------------------------------------------------------------------------
# Domain Rules (search whitelist / blacklist)
# ---------------------------------------------------------------------------

@bp.get("/domain-rules")
@require_auth
@require_admin
async def list_domain_rules(request: Request):
    rules = await DomainRule.select().order_by(DomainRule.domain).run()
    return success(rules)


@bp.post("/domain-rules")
@require_auth
@require_admin
async def create_domain_rule(request: Request):
    try:
        body = DomainRuleRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    await DomainRule.insert(
        DomainRule(
            id=str(uuid.uuid4()),
            domain=body.domain,
            rule_type=body.rule_type,
        )
    ).run()

    return success(message="Domain rule created", status=201)


@bp.delete("/domain-rules/<rule_id:str>")
@require_auth
@require_admin
async def delete_domain_rule(request: Request, rule_id: str):
    await DomainRule.delete().where(DomainRule.id == rule_id).run()
    return success(message="Domain rule deleted")


@bp.put("/domain-rules/<rule_id:str>")
@require_auth
@require_admin
async def update_domain_rule(request: Request, rule_id: str):
    try:
        body = DomainRuleRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    existing = await DomainRule.select().where(DomainRule.id == rule_id).first().run()
    if not existing:
        return error("Domain rule not found", status=404)

    await DomainRule.update({
        DomainRule.domain: body.domain,
        DomainRule.rule_type: body.rule_type,
    }).where(DomainRule.id == rule_id).run()

    updated = await DomainRule.select().where(DomainRule.id == rule_id).first().run()
    return success(updated, message="Domain rule updated")


# ---------------------------------------------------------------------------
# Subscription Plans
# ---------------------------------------------------------------------------

@bp.get("/plans")
@require_auth
@require_admin
async def list_plans(request: Request):
    plans = await SubscriptionPlan.select().order_by(SubscriptionPlan.price_monthly).run()
    return success(plans)


@bp.put("/plans/<plan_id:str>")
@require_auth
@require_admin
async def update_plan(request: Request, plan_id: str):
    try:
        body = PlanUpdateRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error("No fields to update", status=422)

    await SubscriptionPlan.update(updates).where(SubscriptionPlan.id == plan_id).run()

    return success(message="Plan updated")


# ---------------------------------------------------------------------------
# Global MCP Servers
# ---------------------------------------------------------------------------

@bp.post("/mcp-servers")
@require_auth
@require_admin
async def create_global_mcp(request: Request):
    body = request.json
    server_id = str(uuid.uuid4())

    encrypted_key = ""
    if body.get("api_key"):
        encrypted_key = encrypt(body["api_key"])

    await MCPServer.insert(
        MCPServer(
            id=server_id,
            user=None,
            name=body["name"],
            url=body["url"],
            api_key_encrypted=encrypted_key,
            description=body.get("description", ""),
            is_global=True,
            transport=body.get("transport", "sse"),
            headers=body.get("headers", {}),
            metadata=body.get("metadata", {}),
        )
    ).run()

    return success({"id": server_id}, message="Global MCP server created", status=201)


@bp.get("/mcp-servers")
@require_auth
@require_admin
async def list_global_mcp(request: Request):
    servers = await MCPServer.select().where(MCPServer.is_global == True).run()
    for s in servers:
        s.pop("api_key_encrypted", None)
    return success(servers)


@bp.put("/mcp-servers/<server_id:str>")
@require_auth
@require_admin
async def update_global_mcp(request: Request, server_id: str):
    updates = request.json or {}
    if "api_key" in updates:
        updates["api_key_encrypted"] = encrypt(updates.pop("api_key"))
    if updates:
        await MCPServer.update(updates).where(MCPServer.id == server_id).run()
    return success(message="MCP server updated")


@bp.delete("/mcp-servers/<server_id:str>")
@require_auth
@require_admin
async def delete_global_mcp(request: Request, server_id: str):
    await MCPServer.delete().where(MCPServer.id == server_id).run()
    return success(message="MCP server deleted")


# ---------------------------------------------------------------------------
# Contact Requests
# ---------------------------------------------------------------------------

@bp.get("/contact-requests")
@require_auth
@require_admin
async def list_contact_requests(request: Request):
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    offset = (page - 1) * per_page

    requests_list = await ContactRequest.select().order_by(
        ContactRequest.created_at, ascending=False
    ).limit(per_page).offset(offset).run()

    total = await ContactRequest.count().run()
    return paginated(requests_list, total, page, per_page)


@bp.put("/contact-requests/<request_id:str>")
@require_auth
@require_admin
async def resolve_contact_request(request: Request, request_id: str):
    body = request.json or {}
    status_value = body.get("status", "resolved")
    reply = body.get("reply", "")

    updates = {
        ContactRequest.is_resolved: True,
        ContactRequest.resolved_by: request.ctx.user["email"],
    }

    await ContactRequest.update(updates).where(
        ContactRequest.id == request_id
    ).run()

    # If a reply was provided, send it via email (best-effort)
    if reply:
        try:
            contact_req = await ContactRequest.select().where(
                ContactRequest.id == request_id
            ).first().run()
            if contact_req:
                from utils.email import send_email
                await send_email(
                    to=contact_req["email"],
                    subject=f"Re: {contact_req.get('subject', 'Your request')}",
                    text_body=reply,
                )
        except Exception:
            pass  # Non-critical

    return success(message="Contact request resolved")


# ---------------------------------------------------------------------------
# Hot-reload configuration
# ---------------------------------------------------------------------------

@bp.post("/reload-config")
@require_auth
@require_admin
async def reload_config(request: Request):
    """Hot-reload the YAML configuration."""
    from config import settings
    settings.reload()
    return success(message="Configuration reloaded")
