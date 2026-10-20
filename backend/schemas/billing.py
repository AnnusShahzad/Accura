"""
Accura – Billing & Subscription Schemas
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateSubscriptionRequest(BaseModel):
    plan_name: str = Field(pattern="^(basic|pro|business)$")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    payment_method_id: Optional[str] = None  # Stripe payment method


class CancelSubscriptionRequest(BaseModel):
    reason: str = ""


class SubscriptionResponse(BaseModel):
    id: str
    plan_name: str
    billing_cycle: str
    status: str
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    created_at: str


class TransactionResponse(BaseModel):
    id: str
    amount: float
    currency: str
    status: str
    description: str
    created_at: str


class TokenUsageResponse(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    period_start: str
    period_end: str
    breakdown: list[dict] = []


class PlanResponse(BaseModel):
    id: str
    name: str
    display_name: str
    price_monthly: float
    price_yearly: float
    requests_per_minute: int
    requests_per_day: int
    max_tokens_per_request: int
    features: list[str]
