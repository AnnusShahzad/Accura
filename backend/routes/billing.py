"""
Accura – Billing Routes
GET    /api/v1/billing/plans
POST   /api/v1/billing/subscribe
POST   /api/v1/billing/cancel
GET    /api/v1/billing/subscription
GET    /api/v1/billing/transactions
GET    /api/v1/billing/tokens
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from models.subscription import Subscription, SubscriptionPlan
from schemas.billing import CancelSubscriptionRequest, CreateSubscriptionRequest
from services.billing_service import (
    cancel_subscription,
    create_subscription,
    get_plans,
    get_transactions,
)
from services.token_tracker import get_user_token_usage
from utils.exceptions import BillingError, NotFoundError
from utils.responses import error, success, validation_error, int_arg

bp = Blueprint("billing", url_prefix="/api/v1/billing")


@bp.get("/plans")
async def list_plans(request: Request):
    """Public endpoint – list available subscription plans."""
    plans = await get_plans(active_only=True)
    return success(plans)


@bp.post("/subscribe")
@require_auth
async def subscribe(request: Request):
    try:
        body = CreateSubscriptionRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])

    # Business tier requires contact
    if body.plan_name == "business":
        return error(
            "Business accounts require contacting us. Please use the Contact page.",
            status=403,
        )

    try:
        sub = await create_subscription(
            user_id=user_id,
            plan_name=body.plan_name,
            billing_cycle=body.billing_cycle,
        )
    except (NotFoundError, BillingError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(sub, message="Subscription created", status=201)


@bp.post("/cancel")
@require_auth
async def cancel(request: Request):
    user_id = str(request.ctx.user["id"])

    try:
        await cancel_subscription(user_id)
    except NotFoundError as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Subscription cancelled – reverted to Basic")


@bp.get("/subscription")
@require_auth
async def get_subscription(request: Request):
    user_id = str(request.ctx.user["id"])

    sub = await Subscription.select().where(
        (Subscription.user == user_id) & (Subscription.status == "active")
    ).first().run()

    if not sub:
        return success({"plan": "basic", "status": "active"})

    plan = await SubscriptionPlan.select().where(
        SubscriptionPlan.id == sub["plan"]
    ).first().run()

    sub["plan_details"] = plan
    return success(sub)


@bp.get("/transactions")
@require_auth
async def transactions(request: Request):
    user_id = str(request.ctx.user["id"])
    limit = int_arg(request, "limit", 50, minimum=1, maximum=100)
    offset = int_arg(request, "offset", 0)

    txns = await get_transactions(user_id, limit=limit, offset=offset)
    return success(txns)


@bp.get("/tokens")
@require_auth
async def token_usage(request: Request):
    user_id = str(request.ctx.user["id"])

    # Default to current month
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = now

    usage = await get_user_token_usage(user_id, period_start=period_start, period_end=period_end)
    return success(usage)
