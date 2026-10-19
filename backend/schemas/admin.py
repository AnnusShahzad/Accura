"""
Accura – Admin Schemas
"""

from __future__ import annotations

from typing import Optional

from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminConfigUpdateRequest(BaseModel):
    # Dotted path into the configuration, e.g. "evaluation.global_threshold"
    key: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_\-]+(\.[A-Za-z0-9_\-]+)*$")
    value: dict | list | bool | int | float | str | None
    description: str = Field(default="", max_length=2000)


class AdminUserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_admin: Optional[bool] = None
    tier: Optional[str] = Field(None, pattern="^(basic|pro|business)$")


class SystemPromptUpdateRequest(BaseModel):
    role: str = Field(pattern="^(generator|evaluator|reprompt)$")
    prompt: str = Field(min_length=1)
    version: str = Field(default="1.0")


class DomainRuleRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=500)
    rule_type: str = Field(pattern="^(whitelist|blacklist)$")

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if "://" in v:
            v = urlparse(v).netloc
        v = v.removeprefix("www.").split("/")[0]
        if not v or "." not in v or " " in v:
            raise ValueError("Enter a domain like example.com")
        return v


class ContactResolveRequest(BaseModel):
    status: str = Field(default="resolved", pattern="^(resolved|open)$")
    reply: str = Field(default="", max_length=20000)


class PlanUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    price_monthly: Optional[float] = Field(None, ge=0)
    price_yearly: Optional[float] = Field(None, ge=0)
    requests_per_minute: Optional[int] = Field(None, ge=1)
    requests_per_day: Optional[int] = Field(None, ge=1)
    max_tokens_per_request: Optional[int] = Field(None, ge=1)
    features: Optional[list[str]] = None
    is_active: Optional[bool] = None


class AdminDashboardResponse(BaseModel):
    total_users: int
    active_subscriptions: int
    total_revenue: float
    tokens_generated_month: int
    tier_distribution: dict
    recent_transactions: list[dict]


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    company: str = Field(default="", max_length=255)
    subject: str = Field(default="", max_length=500)
    message: str = Field(min_length=1, max_length=10000)
    request_type: str = Field(default="general", pattern="^(general|business_upgrade|support)$")
