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
        engine = Conversation._meta.db
        if not isinstance(engine, SQLiteEngine):
            await engine.start_connection_pool()
        await ensure_schema()
        await _seed_subscription_plans()

    @app.after_server_stop
    async def shutdown(app_instance):
        engine = Conversation._meta.db
        if not isinstance(engine, SQLiteEngine):
            await engine.close_connection_pool()

    return app


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
