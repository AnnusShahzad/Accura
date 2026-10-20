"""
Accura – Public configuration
GET /api/v1/public/config   What the frontend needs to know before login
"""

from __future__ import annotations

from sanic import Blueprint, Request

from config import settings
from services.billing_service import stripe_enabled
from utils.responses import success

bp = Blueprint("public", url_prefix="/api/v1/public")

_PROVIDERS = ("openai", "deepseek", "anthropic", "google", "custom")


def available_providers() -> list[str]:
    """Providers the platform itself has a key for (users can add more)."""
    out = []
    for name in _PROVIDERS:
        if not settings.get(f"ai.providers.{name}.api_key"):
            continue
        if name == "custom" and not settings.get("ai.providers.custom.base_url"):
            continue
        out.append(name)
    return out


@bp.get("/config")
async def public_config(request: Request):
    default_provider = settings.get("ai.default_provider") or "openai"
    return success({
        "registration_enabled": bool(settings.get("auth.registration_enabled", True)),
        "guest": {
            "enabled": bool(settings.get("auth.guest.enabled", False)),
            "ttl_hours": int(settings.get("auth.guest.ttl_hours", 24)),
            "max_iterations": int(settings.get("auth.guest.max_iterations", 3)),
            "requests_per_day": int(settings.get("auth.guest.requests_per_day", 30)),
        },
        "billing_mode": "stripe" if stripe_enabled() else "demo",
        "search_enabled": bool(
            settings.get("search.enabled", True)
            and settings.get("search.google_api_key")
            and settings.get("search.google_cse_id")
        ),
        "ai": {
            "available_providers": available_providers(),
            "default_provider": default_provider,
            "default_generator_model": settings.get("ai.default_generator_model") or "gpt-5.2",
            "default_evaluator_model": settings.get("ai.default_evaluator_model") or "gpt-5.1",
        },
        "branding": {
            "company_name": settings.get("branding.company_name", "Accura"),
            "support_email": settings.get("branding.support_email", ""),
        },
    })
