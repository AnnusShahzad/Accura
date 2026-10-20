"""
Accura – Billing / Subscription Service
Handles subscription lifecycle, Stripe Checkout + webhooks, and
transaction logging.

Two modes:
  * Stripe mode (billing.stripe_secret_key set): paid upgrades go through
    Stripe Checkout and become active when Stripe's webhook confirms them.
  * Demo mode (no key): upgrades apply immediately and a "succeeded"
    transaction is recorded; nothing is charged. Periods renew
    automatically via ``renew_due_subscriptions``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from config import settings
from models.subscription import Subscription, SubscriptionPlan, Transaction
from models.user import User
from utils.exceptions import BillingError, NotFoundError

logger = logging.getLogger("accura.billing_service")

_STRIPE_API = "https://api.stripe.com/v1"
_WEBHOOK_TOLERANCE_SECONDS = 300


def stripe_enabled() -> bool:
    return bool(settings.get("billing.stripe_secret_key", ""))


def _period_end(start: datetime, billing_cycle: str) -> datetime:
    return start + (timedelta(days=365) if billing_cycle == "yearly" else timedelta(days=30))


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

async def get_plans(active_only: bool = True) -> list[dict]:
    query = SubscriptionPlan.select()
    if active_only:
        query = query.where(SubscriptionPlan.is_active == True)  # noqa: E712
    return await query.order_by(SubscriptionPlan.price_monthly).run()


async def get_plan_by_name(name: str) -> dict | None:
    return await SubscriptionPlan.select().where(
        SubscriptionPlan.name == name
    ).first().run()


# ---------------------------------------------------------------------------
# Current subscription
# ---------------------------------------------------------------------------

async def get_current_subscription(user_id: str) -> dict:
    """Return the user's subscription in one stable shape.

    Users on the free tier have no row; they get a synthetic "basic" entry
    so the frontend never has to special-case a missing subscription.
    """
    sub = await Subscription.select().where(
        (Subscription.user == user_id) & (Subscription.status.is_in(["active", "past_due"]))
    ).order_by(Subscription.created_at, ascending=False).first().run()

    user = await User.select(User.tier).where(User.id == user_id).first().run()
    tier = user["tier"] if user else "basic"

    if not sub:
        plan = await get_plan_by_name(tier)
        return {
            "id": None,
            "plan_name": tier,
            "billing_cycle": "monthly",
            "status": "active",
            "current_period_start": None,
            "current_period_end": None,
            "cancelled_at": None,
            "created_at": None,
            "plan_details": plan,
            "billing_mode": "stripe" if stripe_enabled() else "demo",
        }

    plan = await SubscriptionPlan.select().where(SubscriptionPlan.id == sub["plan"]).first().run()
    return {
        "id": str(sub["id"]),
        "plan_name": plan["name"] if plan else tier,
        "billing_cycle": sub["billing_cycle"],
        "status": sub["status"],
        "current_period_start": sub["current_period_start"],
        "current_period_end": sub["current_period_end"],
        "cancelled_at": sub["cancelled_at"],
        "created_at": sub["created_at"],
        "plan_details": plan,
        "billing_mode": "stripe" if stripe_enabled() else "demo",
    }


# ---------------------------------------------------------------------------
# Subscribe / Upgrade
# ---------------------------------------------------------------------------

async def create_subscription(
    user_id: str,
    plan_name: str,
    billing_cycle: str = "monthly",
    stripe_subscription_id: str = "",
    stripe_customer_id: str = "",
    stripe_payment_id: str = "",
) -> dict:
    """Activate *plan_name* for the user (replacing any current plan)."""

    plan = await get_plan_by_name(plan_name)
    if not plan or not plan["is_active"]:
        raise NotFoundError(f"Plan '{plan_name}' not found")

    now = datetime.now(timezone.utc)

    # Deactivate any existing subscription
    await Subscription.update({
        Subscription.status: "cancelled",
        Subscription.cancelled_at: now,
        Subscription.updated_at: now,
    }).where(
        (Subscription.user == user_id) & (Subscription.status.is_in(["active", "past_due"]))
    ).run()

    period_end = _period_end(now, billing_cycle)

    sub_id = str(uuid.uuid4())
    await Subscription.insert(
        Subscription(
            id=sub_id,
            user=user_id,
            plan=plan["id"],
            billing_cycle=billing_cycle,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status="active",
            current_period_start=now,
            current_period_end=period_end,
        )
    ).run()

    # Update user tier
    await User.update({User.tier: plan_name, User.updated_at: now}).where(User.id == user_id).run()

    # Log transaction
    price = plan["price_yearly"] if billing_cycle == "yearly" else plan["price_monthly"]
    if price > 0:
        await Transaction.insert(
            Transaction(
                id=str(uuid.uuid4()),
                user=user_id,
                subscription=sub_id,
                amount=price,
                currency="USD",
                status="succeeded",
                stripe_payment_id=stripe_payment_id,
                description=f"Subscription: {plan['display_name']} ({billing_cycle})"
                + ("" if stripe_subscription_id else " – demo, not charged"),
            )
        ).run()

    logger.info("User %s subscribed to %s (%s)", user_id, plan_name, billing_cycle)

    return await get_current_subscription(user_id)


# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------

async def _stripe(method: str, path: str, data: dict | None = None) -> dict:
    key = settings.get("billing.stripe_secret_key", "")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.request(method, f"{_STRIPE_API}{path}", data=data, auth=(key, ""))
    except httpx.HTTPError as exc:
        raise BillingError(f"Could not reach Stripe: {exc}")
    body = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        message = body.get("error", {}).get("message", resp.text[:200])
        raise BillingError(f"Stripe error: {message}")
    return body


async def create_checkout_session(user: dict, plan_name: str, billing_cycle: str) -> str:
    """Start a Stripe Checkout session and return its URL."""
    price_id = settings.get(f"billing.stripe_price_ids.{plan_name}_{billing_cycle}", "")
    if not price_id:
        raise BillingError(
            f"No Stripe price configured for {plan_name} ({billing_cycle}). "
            f"Set STRIPE_PRICE_{plan_name.upper()}_{billing_cycle.upper()}."
        )
    frontend = settings.get("app.frontend_url", "http://localhost:3000").rstrip("/")
    meta = {"user_id": str(user["id"]), "plan_name": plan_name, "billing_cycle": billing_cycle}
    data = {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "customer_email": user["email"],
        "client_reference_id": str(user["id"]),
        "success_url": f"{frontend}/settings/billing?checkout=success",
        "cancel_url": f"{frontend}/settings/billing?checkout=cancelled",
    }
    for k, v in meta.items():
        data[f"metadata[{k}]"] = v
        data[f"subscription_data[metadata][{k}]"] = v
    session = await _stripe("POST", "/checkout/sessions", data)
    return session["url"]


def verify_stripe_signature(payload: bytes, header: str, secret: str) -> dict:
    """Validate a Stripe-Signature header and return the parsed event."""
    try:
        parts = dict(item.split("=", 1) for item in header.split(",") if "=" in item)
        timestamp = int(parts["t"])
    except (KeyError, ValueError):
        raise BillingError("Malformed Stripe-Signature header")
    signatures = [v for k, v in (item.split("=", 1) for item in header.split(",") if "=" in item) if k == "v1"]
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise BillingError("Invalid Stripe signature")
    if abs(time.time() - timestamp) > _WEBHOOK_TOLERANCE_SECONDS:
        raise BillingError("Stripe webhook timestamp outside tolerance")
    return json.loads(payload)


async def handle_stripe_event(event: dict) -> None:
    kind = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if kind == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        if not meta.get("user_id"):
            logger.warning("Checkout session %s without user metadata", obj.get("id"))
            return
        await create_subscription(
            user_id=meta["user_id"],
            plan_name=meta.get("plan_name", "pro"),
            billing_cycle=meta.get("billing_cycle", "monthly"),
            stripe_subscription_id=obj.get("subscription") or "",
            stripe_customer_id=obj.get("customer") or "",
            stripe_payment_id=obj.get("payment_intent") or obj.get("invoice") or "",
        )

    elif kind == "invoice.paid":
        stripe_sub = obj.get("subscription")
        sub = await Subscription.select().where(
            Subscription.stripe_subscription_id == stripe_sub
        ).first().run() if stripe_sub else None
        # The first invoice is recorded by checkout.session.completed
        if not sub or obj.get("billing_reason") == "subscription_create":
            return
        now = datetime.now(timezone.utc)
        await Subscription.update({
            Subscription.status: "active",
            Subscription.current_period_start: now,
            Subscription.current_period_end: _period_end(now, sub["billing_cycle"]),
            Subscription.updated_at: now,
        }).where(Subscription.id == sub["id"]).run()
        await Transaction.insert(
            Transaction(
                id=str(uuid.uuid4()),
                user=sub["user"],
                subscription=sub["id"],
                amount=(obj.get("amount_paid") or 0) / 100,
                currency=(obj.get("currency") or "usd").upper(),
                status="succeeded",
                stripe_payment_id=obj.get("id", ""),
                description="Subscription renewal",
            )
        ).run()

    elif kind == "invoice.payment_failed":
        stripe_sub = obj.get("subscription")
        if stripe_sub:
            await Subscription.update({Subscription.status: "past_due"}).where(
                Subscription.stripe_subscription_id == stripe_sub
            ).run()

    elif kind == "customer.subscription.deleted":
        sub = await Subscription.select().where(
            Subscription.stripe_subscription_id == obj.get("id", "")
        ).first().run()
        if sub and sub["status"] != "cancelled":
            await _end_subscription(sub)


# ---------------------------------------------------------------------------
# Cancel / renew
# ---------------------------------------------------------------------------

async def _end_subscription(sub: dict) -> None:
    now = datetime.now(timezone.utc)
    await Subscription.update({
        Subscription.status: "cancelled",
        Subscription.cancelled_at: now,
        Subscription.updated_at: now,
    }).where(Subscription.id == sub["id"]).run()
    await User.update({User.tier: "basic", User.updated_at: now}).where(User.id == sub["user"]).run()


async def cancel_subscription(user_id: str) -> bool:
    """Cancel active subscription and revert user to basic."""
    sub = await Subscription.select().where(
        (Subscription.user == user_id) & (Subscription.status.is_in(["active", "past_due"]))
    ).first().run()

    if not sub:
        raise NotFoundError("No active subscription found")

    if sub["stripe_subscription_id"] and stripe_enabled():
        await _stripe("DELETE", f"/subscriptions/{sub['stripe_subscription_id']}")

    await _end_subscription(sub)
    logger.info("User %s cancelled subscription", user_id)
    return True


async def renew_due_subscriptions() -> int:
    """Roll demo-mode subscriptions whose period ended into a new period.

    Stripe-managed subscriptions are renewed by Stripe's invoice webhooks
    instead. Returns the number of subscriptions renewed.
    """
    now = datetime.now(timezone.utc)
    due = await Subscription.select().where(
        (Subscription.status == "active")
        & (Subscription.current_period_end <= now)
        & (Subscription.stripe_subscription_id == "")
    ).run()

    renewed = 0
    for sub in due:
        plan = await SubscriptionPlan.select().where(SubscriptionPlan.id == sub["plan"]).first().run()
        if not plan or not plan["is_active"]:
            await _end_subscription(sub)
            continue
        start = sub["current_period_end"] or now
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        end = _period_end(start, sub["billing_cycle"])
        while end <= now:  # catch up if the server was down for a while
            start, end = end, _period_end(end, sub["billing_cycle"])
        await Subscription.update({
            Subscription.current_period_start: start,
            Subscription.current_period_end: end,
            Subscription.updated_at: now,
        }).where(Subscription.id == sub["id"]).run()
        price = plan["price_yearly"] if sub["billing_cycle"] == "yearly" else plan["price_monthly"]
        if price > 0:
            await Transaction.insert(
                Transaction(
                    id=str(uuid.uuid4()),
                    user=sub["user"],
                    subscription=sub["id"],
                    amount=price,
                    currency="USD",
                    status="succeeded",
                    description=f"Renewal: {plan['display_name']} ({sub['billing_cycle']}) – demo, not charged",
                )
            ).run()
        renewed += 1
    if renewed:
        logger.info("Renewed %d subscription(s)", renewed)
    return renewed


# ---------------------------------------------------------------------------
# Transaction history
# ---------------------------------------------------------------------------

async def get_transactions(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    return await Transaction.select().where(
        Transaction.user == user_id
    ).order_by(Transaction.created_at, ascending=False).limit(limit).offset(offset).run()


# ---------------------------------------------------------------------------
# Admin: revenue dashboard
# ---------------------------------------------------------------------------

async def get_revenue_summary() -> dict:
    """Aggregate revenue data for admin dashboard."""
    transactions = await Transaction.select(Transaction.amount).where(
        Transaction.status == "succeeded"
    ).run()

    total = sum(float(t["amount"]) for t in transactions)

    return {
        "total_revenue": round(total, 2),
        "transaction_count": len(transactions),
    }
