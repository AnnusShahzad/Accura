"""
Accura – Main Application Entry Point
"""

from __future__ import annotations

import logging

from piccolo.engine.sqlite import SQLiteEngine
from sanic import Sanic, json as sanic_json
from sanic.request import Request

from config import settings
from models.chat import Conversation
from utils.db_schema import ensure_schema
from middleware.auth_middleware import auth_middleware
from middleware.rate_limiter import rate_limit_middleware
from routes.admin import bp as admin_bp
from routes.api_keys import bp as api_keys_bp
from routes.auth import bp as auth_bp
from routes.billing import bp as billing_bp
from routes.chat import bp as chat_bp
from routes.contact import bp as contact_bp
from routes.mcp import bp as mcp_bp
from routes.notifications import bp as notifications_bp
from routes.settings import bp as settings_bp
from routes.user import bp as user_bp

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.get("app.debug") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("accura")
# Library chatter that drowns out our own logs in debug mode
for _name in ("aiosqlite", "asyncio", "httpcore", "httpx", "openai", "hpack"):
    logging.getLogger(_name).setLevel(logging.INFO if _name == "httpx" else logging.WARNING)


def _dedupe_sanic_logs() -> None:
    # Sanic attaches its own handlers (and re-applies its logging config
    # when the app is created); without this every Sanic line is printed
    # twice, once by Sanic and once by the root handler above.
    for name in ("sanic.root", "sanic.error", "sanic.access", "sanic.server", "sanic.websockets"):
        logging.getLogger(name).propagate = False

_INSECURE_SECRETS = {"", "changeme", "change-me-in-production", "change-me-to-a-secure-random-string"}


def _check_secrets() -> None:
    """Refuse to boot in production with placeholder secrets."""
    problems = []
    if str(settings.get("jwt.secret", "")) in _INSECURE_SECRETS:
        problems.append("JWT_SECRET is unset or a placeholder")
    if not settings.get("security.encryption_key"):
        problems.append("ENCRYPTION_KEY is unset (saving API keys will fail)")
    if not problems:
        return
    if str(settings.get("app.environment", "")).lower() == "production" and not settings.get("app.debug"):
        raise RuntimeError("Insecure configuration: " + "; ".join(problems))
    for problem in problems:
        logger.warning("Insecure configuration: %s", problem)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> Sanic:
    # strict_slashes=False: "/api/v1/chat" and "/api/v1/chat/" are the same route
    app = Sanic("Accura", strict_slashes=False)

    # --- Configuration / CORS (handled by sanic-ext, incl. preflight) ---
    origins = str(settings.get("app.cors_origins", "*") or "*")
    app.config.update({
        "CORS_ORIGINS": origins if origins == "*" else [o.strip() for o in origins.split(",") if o.strip()],
        "CORS_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "CORS_ALLOW_HEADERS": ["Authorization", "Content-Type", "Stripe-Signature"],
        "CORS_MAX_AGE": 600,
        "FALLBACK_ERROR_FORMAT": "json",
        "OAS_UI_DEFAULT": "swagger",
    })

    # --- Middleware ---
    app.register_middleware(auth_middleware, "request")
    app.register_middleware(rate_limit_middleware, "request")

    # --- Blueprints ---
    app.blueprint(auth_bp)
    app.blueprint(user_bp)
    app.blueprint(chat_bp)
    app.blueprint(settings_bp)
    app.blueprint(mcp_bp)
    app.blueprint(api_keys_bp)
    app.blueprint(billing_bp)
    app.blueprint(notifications_bp)
    app.blueprint(contact_bp)
    app.blueprint(admin_bp)

    # --- Health check ---
    @app.get("/api/v1/health")
    async def health(request: Request):
        return sanic_json({
            "status": "healthy",
            "version": settings.get("app.version", "1.0.0"),
            "environment": settings.get("app.environment", "unknown"),
        })

    # --- Error handler ---
    @app.exception(Exception)
    async def global_error_handler(request: Request, exception: Exception):
        status = getattr(exception, "status_code", 500)
        message = getattr(exception, "message", str(exception))
        if status >= 500:
            logger.exception("Unhandled error: %s", exception)
        return sanic_json(
            {"success": False, "message": message},
            status=status,
        )

    # --- Startup event: create tables & seed data ---
    @app.before_server_start
    async def startup(app_instance):
        logger.info("Accura backend starting – %s", settings.get("app.environment"))
        _check_secrets()
        engine = Conversation._meta.db
        if not isinstance(engine, SQLiteEngine) and getattr(engine, "pool", None) is None:
            await engine.start_connection_pool()
        await ensure_schema()
        await _seed_subscription_plans()
        from routes.admin import apply_admin_config

        await apply_admin_config()

    @app.after_server_start
    async def start_background_jobs(app_instance):
        app_instance.add_task(_renewal_loop(), name="subscription-renewals")

    @app.before_server_stop
    async def stop_background_jobs(app_instance):
        await app_instance.cancel_task("subscription-renewals", raise_exception=False)

    @app.after_server_stop
    async def shutdown(app_instance):
        engine = Conversation._meta.db
        # The ASGI test client runs the server lifecycle around every
        # request; it sets keep_db_pool so background tasks keep working.
        if not isinstance(engine, SQLiteEngine) and not getattr(app_instance.ctx, "keep_db_pool", False):
            await engine.close_connection_pool()

    _dedupe_sanic_logs()
    return app


async def _renewal_loop():
    """Periodically roll over subscriptions whose billing period ended."""
    import asyncio

    from services.billing_service import renew_due_subscriptions

    interval = max(60, int(settings.get("billing.renewal_check_interval", 3600)))
    while True:
        try:
            await renew_due_subscriptions()
        except Exception:
            logger.exception("Subscription renewal job failed")
        await asyncio.sleep(interval)


async def _seed_subscription_plans():
    """Ensure default subscription plans exist."""
    import decimal
    import uuid

    from models.subscription import SubscriptionPlan

    for plan_name in ("basic", "pro", "business"):
        existing = await SubscriptionPlan.select().where(
            SubscriptionPlan.name == plan_name
        ).first().run()
        if not existing:
            plan_config = settings.get(f"subscriptions.{plan_name}", {})
            raw_monthly = plan_config.get("price_monthly", 0)
            raw_yearly = plan_config.get("price_yearly", 0)
            await SubscriptionPlan.insert(
                SubscriptionPlan(
                    id=str(uuid.uuid4()),
                    name=plan_name,
                    display_name=plan_name.capitalize(),
                    price_monthly=decimal.Decimal(str(raw_monthly)),
                    price_yearly=decimal.Decimal(str(raw_yearly)),
                    requests_per_minute=settings.get(f"rate_limits.{plan_name}.requests_per_minute", 10),
                    requests_per_day=settings.get(f"rate_limits.{plan_name}.requests_per_day", 100),
                    max_tokens_per_request=settings.get(f"rate_limits.{plan_name}.max_tokens_per_request", 4096),
                    features=plan_config.get("features", []),
                )
            ).run()
            logger.info("Seeded subscription plan: %s", plan_name)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    workers = max(1, int(settings.get("app.workers", 1)))
    app.run(
        host=settings.get("app.host", "0.0.0.0"),
        port=int(settings.get("app.port", 8000)),
        debug=bool(settings.get("app.debug", False)),
        workers=workers,
        single_process=workers == 1,
    )
