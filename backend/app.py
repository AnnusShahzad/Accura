"""
Accura – Main Application Entry Point
"""

from __future__ import annotations

import logging
import os

from sanic import Sanic, json as sanic_json
from sanic.request import Request

from config import settings
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
    app = Sanic("Accura")

    # --- Configuration ---
    app.config.update({
        "CORS_ORIGINS": "*",
        "CORS_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "CORS_HEADERS": ["Authorization", "Content-Type"],
        "FALLBACK_ERROR_FORMAT": "json",
    })

    # --- CORS ---
    @app.options("/<path:path>")
    async def cors_preflight(request: Request, path: str):
        return sanic_json("", status=204)

    @app.middleware("response")
    async def add_cors_headers(request: Request, response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type"

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

    # --- Startup event: seed data ---
    @app.before_server_start
    async def startup(app_instance, loop):
        logger.info("Accura backend starting – %s", settings.get("app.environment"))
        await _seed_subscription_plans()

    return app


async def _seed_subscription_plans():
    """Ensure default subscription plans exist."""
    from models.subscription import SubscriptionPlan
    import uuid

    for plan_name in ("basic", "pro", "business"):
        existing = await SubscriptionPlan.select().where(
            SubscriptionPlan.name == plan_name
        ).first().run()
        if not existing:
            plan_config = settings.get(f"subscriptions.{plan_name}", {})
            await SubscriptionPlan.insert(
                SubscriptionPlan(
                    id=str(uuid.uuid4()),
                    name=plan_name,
                    display_name=plan_name.capitalize(),
                    price_monthly=plan_config.get("price_monthly", 0),
                    price_yearly=plan_config.get("price_yearly", 0),
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
    app.run(
        host=settings.get("app.host", "0.0.0.0"),
        port=settings.get("app.port", 8000),
        workers=settings.get("app.workers", 1),
        debug=settings.get("app.debug", False),
        auto_reload=settings.get("app.debug", False),
    )
