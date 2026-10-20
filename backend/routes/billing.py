"""
Accura – Billing Routes
GET    /api/v1/billing/plans
POST   /api/v1/billing/subscribe
POST   /api/v1/billing/cancel
GET    /api/v1/billing/subscription
GET    /api/v1/billing/transactions
GET    /api/v1/billing/tokens
POST   /api/v1/billing/webhook          Stripe webhook (signature verified)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sanic import Blueprint, Request

from config import settings
from middleware.auth_middleware import require_auth
from schemas.billing import CreateSubscriptionRequest
from services.billing_service import (
    cancel_subscription,
    create_checkout_session,
    create_subscription,
    get_current_subscription,
    get_plan_by_name,
    get_plans,
    get_transactions,
    handle_stripe_event,
    stripe_enabled,
    verify_stripe_signature,
)
from services.token_tracker import get_user_token_usage
from utils.exceptions import BillingError, NotFoundError
from utils.responses import error, success, validation_error, int_arg

logger = logging.getLogger("accura.billing")

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

    user = request.ctx.user
    user_id = str(user["id"])

    if user.get("is_guest"):
        return error("Guest accounts can't change plans. Sign in with a full account to upgrade.", status=403)

    # Business tier requires contact
    if body.plan_name == "business":
        return error(
            "Business accounts require contacting us. Please use the contact form.",
            status=403,
        )

    plan = await get_plan_by_name(body.plan_name)
    if not plan or not plan["is_active"]:
        return error(f"Plan '{body.plan_name}' not found", status=404)

    try:
        # Moving to the free plan is a cancellation of the paid one
        if body.plan_name == "basic":
            try:
                await cancel_subscription(user_id)
            except NotFoundError:
                pass
            return success(await get_current_subscription(user_id), message="You are on the Basic plan")

        price = plan["price_yearly"] if body.billing_cycle == "yearly" else plan["price_monthly"]
        if price > 0 and stripe_enabled():
            url = await create_checkout_session(user, body.plan_name, body.billing_cycle)
            return success({"checkout_url": url}, message="Redirecting to checkout")

        sub = await create_subscription(
            user_id=user_id,
            plan_name=body.plan_name,
            billing_cycle=body.billing_cycle,
        )
    except (NotFoundError, BillingError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(sub, message="Subscription activated", status=201)


@bp.post("/cancel")
@require_auth
async def cancel(request: Request):
    user_id = str(request.ctx.user["id"])
    if request.ctx.user.get("is_guest"):
        return error("Guest accounts don't have a plan to cancel.", status=403)

    try:
        await cancel_subscription(user_id)
    except (NotFoundError, BillingError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Subscription cancelled – reverted to Basic")


@bp.get("/subscription")
@require_auth
async def get_subscription(request: Request):
    return success(await get_current_subscription(str(request.ctx.user["id"])))


@bp.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint. Public, authenticated by signature."""
    secret = settings.get("billing.stripe_webhook_secret", "")
    if not secret:
        return error("Stripe webhooks are not configured", status=503)
    try:
        event = verify_stripe_signature(
            request.body, request.headers.get("Stripe-Signature", ""), secret
        )
    except BillingError as exc:
        return error(exc.message, status=400)
    except ValueError:
        return error("Invalid payload", status=400)

    try:
        await handle_stripe_event(event)
    except Exception:
        # Non-2xx makes Stripe retry, which is what we want here
        logger.exception("Failed to handle Stripe event %s", event.get("id"))
        return error("Webhook handling failed", status=500)
    return success({"received": True})


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
