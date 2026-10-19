"""
Accura – Subscription, Plan & Transaction Models
"""

import decimal

from piccolo.columns import (
    UUID,
    Boolean,
    Integer,
    Numeric,
    Text,
    Timestamptz,
    Varchar,
    JSONB,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from models.base import JSONTable

from models.user import User


class SubscriptionPlan(JSONTable, tablename="subscription_plans"):
    """Admin-managed subscription tiers with pricing."""

    id = UUID(primary_key=True)
    name = Varchar(length=50, unique=True)  # basic | pro | business
    display_name = Varchar(length=100)
    price_monthly = Numeric(digits=(10, 2), default=decimal.Decimal("0"))
    price_yearly = Numeric(digits=(10, 2), default=decimal.Decimal("0"))
    requests_per_minute = Integer(default=10)
    requests_per_day = Integer(default=100)
    max_tokens_per_request = Integer(default=4096)
    features = JSONB(default=[])
    is_active = Boolean(default=True)
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())


class Subscription(Table, tablename="subscriptions"):
    """Active user subscription."""

    id = UUID(primary_key=True)
    user = UUID(references=User, index=True)
    plan = UUID(references=SubscriptionPlan)
    billing_cycle = Varchar(length=10, default="monthly")  # monthly | yearly
    stripe_subscription_id = Varchar(length=255, default="")
    stripe_customer_id = Varchar(length=255, default="")
    status = Varchar(length=20, default="active")  # active | cancelled | past_due
    current_period_start = Timestamptz(null=True, default=None)
    current_period_end = Timestamptz(null=True, default=None)
    cancelled_at = Timestamptz(null=True, default=None)
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())


class Transaction(Table, tablename="transactions"):
    """Billing transaction / payment history."""

    id = UUID(primary_key=True)
    user = UUID(references=User, index=True)
    subscription = UUID(references=Subscription, null=True, default=None)
    amount = Numeric(digits=(10, 2), default=decimal.Decimal("0"))
    currency = Varchar(length=3, default="USD")
    status = Varchar(length=20, default="pending")  # pending | succeeded | failed | refunded
    stripe_payment_id = Varchar(length=255, default="")
    description = Text(default="")
    created_at = Timestamptz(default=TimestamptzNow())
