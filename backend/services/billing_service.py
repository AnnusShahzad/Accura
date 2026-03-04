"""
Accura – Billing / Subscription Service
Handles subscription lifecycle, Stripe integration stubs, and transaction logging.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from models.subscription import Subscription, SubscriptionPlan, Transaction
from models.user import User
from utils.exceptions import BillingError, NotFoundError

logger = logging.getLogger("accura.billing_service")


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

async def get_plans(active_only: bool = True) -> list[dict]:
    query = SubscriptionPlan.select()
    if active_only:
        query = query.where(SubscriptionPlan.is_active == True)
    return await query.order_by(SubscriptionPlan.price_monthly).run()


async def get_plan_by_name(name: str) -> dict | None:
    return await SubscriptionPlan.select().where(
        SubscriptionPlan.name == name
    ).first().run()


# ---------------------------------------------------------------------------
# Subscribe / Upgrade
# ---------------------------------------------------------------------------

async def create_subscription(
    user_id: str,
    plan_name: str,
    billing_cycle: str = "monthly",
    stripe_subscription_id: str = "",
    stripe_customer_id: str = "",
) -> dict:
    """Create or upgrade a user subscription."""

    plan = await get_plan_by_name(plan_name)
    if not plan:
        raise NotFoundError(f"Plan '{plan_name}' not found")

    # Deactivate any existing subscription
    existing = await Subscription.select().where(
        (Subscription.user == user_id) & (Subscription.status == "active")
    ).first().run()
    if existing:
        await Subscription.update({Subscription.status: "cancelled"}).where(
            Subscription.id == existing["id"]
        ).run()

    now = datetime.now(timezone.utc)
    period_end = now + (timedelta(days=365) if billing_cycle == "yearly" else timedelta(days=30))

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
    await User.update({User.tier: plan_name}).where(User.id == user_id).run()

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
                description=f"Subscription: {plan_name} ({billing_cycle})",
            )
        ).run()

    logger.info("User %s subscribed to %s (%s)", user_id, plan_name, billing_cycle)

    return {
        "id": sub_id,
        "plan_name": plan_name,
        "billing_cycle": billing_cycle,
        "status": "active",
        "current_period_start": now.isoformat(),
        "current_period_end": period_end.isoformat(),
    }


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

async def cancel_subscription(user_id: str) -> bool:
    """Cancel active subscription and revert user to basic."""
    sub = await Subscription.select().where(
        (Subscription.user == user_id) & (Subscription.status == "active")
    ).first().run()

    if not sub:
        raise NotFoundError("No active subscription found")

    now = datetime.now(timezone.utc)
    await Subscription.update({
        Subscription.status: "cancelled",
        Subscription.cancelled_at: now,
    }).where(Subscription.id == sub["id"]).run()

    await User.update({User.tier: "basic"}).where(User.id == user_id).run()

    logger.info("User %s cancelled subscription", user_id)
    return True


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
    transactions = await Transaction.select().where(
        Transaction.status == "succeeded"
    ).run()

    total = sum(float(t["amount"]) for t in transactions)

    return {
        "total_revenue": round(total, 2),
        "transaction_count": len(transactions),
    }
