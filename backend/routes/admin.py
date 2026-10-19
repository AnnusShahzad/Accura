"""
Accura – Admin Routes
All routes require admin authentication.

GET    /api/v1/admin/dashboard
GET    /api/v1/admin/users
GET    /api/v1/admin/users/<id>
PUT    /api/v1/admin/users/<id>
GET    /api/v1/admin/config
PUT    /api/v1/admin/config
DELETE /api/v1/admin/config/<key>
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

import json
import uuid
from datetime import datetime, timezone

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
    ContactResolveRequest,
    DomainRuleRequest,
    PlanUpdateRequest,
    SystemPromptUpdateRequest,
)
from schemas.mcp import CreateMCPServerRequest, UpdateMCPServerRequest
from services.billing_service import get_revenue_summary
from utils.crypto import encrypt
from utils.responses import error, paginated, success, validation_error, int_arg

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

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_iters = await Iteration.select(Iteration.tokens_input, Iteration.tokens_output).where(
        Iteration.created_at >= month_start
    ).run()
    tokens_month = sum((i["tokens_input"] or 0) + (i["tokens_output"] or 0) for i in month_iters)
    conversations = await Conversation.count().run()

    return success({
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "total_revenue": revenue["total_revenue"],
        "tokens_generated_month": tokens_month,
        "total_conversations": conversations,
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
    page = int_arg(request, "page", 1, minimum=1)
    per_page = int_arg(request, "per_page", 50, minimum=1, maximum=200)
    offset = (page - 1) * per_page

    search = request.args.get("search", "")

    query = User.select(
        User.id, User.email, User.username, User.tier,
        User.is_active, User.is_verified, User.is_admin, User.created_at,
    )
    count = User.count()
    if search:
        matches = (User.email.ilike(f"%{search}%")) | (User.username.ilike(f"%{search}%"))
        query = query.where(matches)
        count = count.where(matches)

    total = await count.run()
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
    user.pop("otp_code", None)
    return success(user)


@bp.put("/users/<user_id:str>")
@require_auth
@require_admin
async def update_user(request: Request, user_id: str):
    try:
        body = AdminUserUpdateRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error("No fields to update", status=422)

    target = await User.select(User.id).where(User.id == user_id).first().run()
    if not target:
        return error("User not found", status=404)

    # Don't let an admin lock themselves out of the admin panel
    if str(request.ctx.user["id"]) == user_id and (
        updates.get("is_admin") is False or updates.get("is_active") is False
    ):
        return error("You cannot remove your own admin access or deactivate yourself", status=400)

    updates["updated_at"] = datetime.now(timezone.utc)
    await User.update(updates).where(User.id == user_id).run()

    user = await User.select().where(User.id == user_id).first().run()
    user.pop("hashed_password", None)
    user.pop("otp_code", None)
    return success(user, message="User updated")


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
        body = AdminConfigUpdateRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    # Piccolo stores str values for JSON columns verbatim (assuming they
    # are already JSON), so always encode explicitly.
    encoded = json.dumps(body.value)
    now = datetime.now(timezone.utc)

    existing = await AdminConfig.select(AdminConfig.id).where(AdminConfig.key == body.key).first().run()
    if existing:
        await AdminConfig.update({
            AdminConfig.value: encoded,
            AdminConfig.description: body.description,
            AdminConfig.updated_by: request.ctx.user["email"],
            AdminConfig.updated_at: now,
        }).where(AdminConfig.key == body.key).run()
    else:
        await AdminConfig.insert(
            AdminConfig(
                id=str(uuid.uuid4()),
                key=body.key,
                value=encoded,
                description=body.description,
                updated_by=request.ctx.user["email"],
            )
        ).run()

    await apply_admin_config()
    saved = await AdminConfig.select().where(AdminConfig.key == body.key).first().run()
    return success(saved, message="Config updated")


@bp.delete("/config/<key:str>")
@require_auth
@require_admin
async def delete_config(request: Request, key: str):
    existing = await AdminConfig.select(AdminConfig.id).where(AdminConfig.key == key).first().run()
    if not existing:
        return error("Config key not found", status=404)
    await AdminConfig.delete().where(AdminConfig.key == key).run()
    await apply_admin_config()
    return success(message="Config deleted")


async def apply_admin_config() -> None:
    """Load admin_config rows into the runtime settings override layer.

    Keys are dotted config paths (e.g. ``evaluation.global_threshold``),
    so anything in config.yaml can be overridden without a restart.
    """
    from config import settings

    rows = await AdminConfig.select(AdminConfig.key, AdminConfig.value).run()
    settings.apply_overrides({r["key"]: r["value"] for r in rows})


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
        body = SystemPromptUpdateRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

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
        body = SystemPromptUpdateRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    existing = await SystemPrompt.select().where(SystemPrompt.role == body.role).first().run()
    if existing:
        await SystemPrompt.update({
            SystemPrompt.prompt: body.prompt,
            SystemPrompt.version: body.version,
            SystemPrompt.updated_at: datetime.now(timezone.utc),
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
        body = SystemPromptUpdateRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    existing = await SystemPrompt.select().where(SystemPrompt.id == prompt_id).first().run()
    if not existing:
        return error("System prompt not found", status=404)

    # role is unique: moving a prompt onto a role that already has one
    # would violate the constraint and 500
    if body.role != existing["role"]:
        clash = await SystemPrompt.select(SystemPrompt.id).where(SystemPrompt.role == body.role).first().run()
        if clash:
            return error(f"A system prompt for role '{body.role}' already exists", status=409)

    await SystemPrompt.update({
        SystemPrompt.role: body.role,
        SystemPrompt.prompt: body.prompt,
        SystemPrompt.version: body.version,
        SystemPrompt.updated_at: datetime.now(timezone.utc),
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
        body = DomainRuleRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    duplicate = await DomainRule.select(DomainRule.id).where(
        (DomainRule.domain == body.domain) & (DomainRule.rule_type == body.rule_type)
    ).first().run()
    if duplicate:
        return error(f"{body.domain} is already on the {body.rule_type}", status=409)

    rule_id = str(uuid.uuid4())
    await DomainRule.insert(
        DomainRule(
            id=rule_id,
            domain=body.domain,
            rule_type=body.rule_type,
        )
    ).run()

    created = await DomainRule.select().where(DomainRule.id == rule_id).first().run()
    return success(created, message="Domain rule created", status=201)


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
        body = DomainRuleRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

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
        body = PlanUpdateRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error("No fields to update", status=422)

    plan = await SubscriptionPlan.select(SubscriptionPlan.id).where(SubscriptionPlan.id == plan_id).first().run()
    if not plan:
        return error("Plan not found", status=404)

    if "features" in updates:
        updates["features"] = json.dumps(updates["features"])
    updates["updated_at"] = datetime.now(timezone.utc)
    await SubscriptionPlan.update(updates).where(SubscriptionPlan.id == plan_id).run()

    # Rate limits are read from plans; drop the cached values
    from middleware.rate_limiter import _limit_cache
    _limit_cache.clear()

    updated = await SubscriptionPlan.select().where(SubscriptionPlan.id == plan_id).first().run()
    return success(updated, message="Plan updated")


# ---------------------------------------------------------------------------
# Global MCP Servers
# ---------------------------------------------------------------------------

@bp.post("/mcp-servers")
@require_auth
@require_admin
async def create_global_mcp(request: Request):
    try:
        body = CreateMCPServerRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    server_id = str(uuid.uuid4())
    await MCPServer.insert(
        MCPServer(
            id=server_id,
            user=None,
            name=body.name,
            url=body.url,
            api_key_encrypted=encrypt(body.api_key) if body.api_key else "",
            description=body.description,
            is_global=True,
            transport=body.transport,
            headers=body.headers,
            metadata=body.metadata,
        )
    ).run()

    server = await MCPServer.select().where(MCPServer.id == server_id).first().run()
    server.pop("api_key_encrypted", None)
    return success(server, message="Global MCP server created", status=201)


@bp.get("/mcp-servers")
@require_auth
@require_admin
async def list_global_mcp(request: Request):
    servers = await MCPServer.select().where(MCPServer.is_global == True).order_by(  # noqa: E712
        MCPServer.created_at, ascending=False
    ).run()
    for s in servers:
        s.pop("api_key_encrypted", None)
    return success(servers)


@bp.put("/mcp-servers/<server_id:str>")
@require_auth
@require_admin
async def update_global_mcp(request: Request, server_id: str):
    try:
        body = UpdateMCPServerRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    server = await MCPServer.select(MCPServer.id).where(
        (MCPServer.id == server_id) & (MCPServer.is_global == True)  # noqa: E712
    ).first().run()
    if not server:
        return error("Global MCP server not found", status=404)

    updates = body.model_dump(exclude_none=True)
    if "api_key" in updates:
        api_key = updates.pop("api_key")
        updates["api_key_encrypted"] = encrypt(api_key) if api_key else ""
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await MCPServer.update(updates).where(MCPServer.id == server_id).run()

    updated = await MCPServer.select().where(MCPServer.id == server_id).first().run()
    updated.pop("api_key_encrypted", None)
    return success(updated, message="MCP server updated")


@bp.delete("/mcp-servers/<server_id:str>")
@require_auth
@require_admin
async def delete_global_mcp(request: Request, server_id: str):
    # Only global servers: this must not become a way to delete users' servers
    server = await MCPServer.select(MCPServer.id).where(
        (MCPServer.id == server_id) & (MCPServer.is_global == True)  # noqa: E712
    ).first().run()
    if not server:
        return error("Global MCP server not found", status=404)
    await MCPServer.delete().where(MCPServer.id == server_id).run()
    return success(message="MCP server deleted")


# ---------------------------------------------------------------------------
# Contact Requests
# ---------------------------------------------------------------------------

@bp.get("/contact-requests")
@require_auth
@require_admin
async def list_contact_requests(request: Request):
    page = int_arg(request, "page", 1, minimum=1)
    per_page = int_arg(request, "per_page", 50, minimum=1, maximum=200)
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
    try:
        body = ContactResolveRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    contact_req = await ContactRequest.select().where(ContactRequest.id == request_id).first().run()
    if not contact_req:
        return error("Contact request not found", status=404)

    resolved = body.status == "resolved"
    await ContactRequest.update({
        ContactRequest.is_resolved: resolved,
        ContactRequest.resolved_by: request.ctx.user["email"] if resolved else "",
        ContactRequest.updated_at: datetime.now(timezone.utc),
    }).where(ContactRequest.id == request_id).run()

    emailed = False
    if body.reply:
        from utils.email import send_email

        try:
            await send_email(
                to=contact_req["email"],
                subject=f"Re: {contact_req.get('subject') or 'Your request'}",
                text_body=body.reply,
            )
            emailed = True
        except Exception:
            return error("Status saved, but the reply email could not be sent. Check SMTP settings.", status=502)

    message = "Contact request resolved" if resolved else "Contact request reopened"
    if emailed:
        message += " – reply sent"
    return success({"is_resolved": resolved, "emailed": emailed}, message=message)


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
    await apply_admin_config()
    return success(message="Configuration reloaded")
