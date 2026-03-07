"""
Accura – JWT Authentication Middleware
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

import jwt
from sanic import Request
from sanic.response import json as sanic_json

from config import settings
from models.user import User

logger = logging.getLogger("accura.auth")

_JWT_SECRET = settings.get("jwt.secret", "changeme")
_JWT_ALGORITHM = settings.get("jwt.algorithm", "HS256")

_PUBLIC_PATHS: set[str] = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/verify-otp",
    "/api/v1/auth/resend-otp",
    "/api/v1/contact",
    "/api/v1/health",
    "/api/v1/plans",
    "/api/v1/billing/plans",
}

def _is_public(path: str) -> bool:
    if path.startswith("/api/v1/auth/check-username/"):
        return True
    return path in _PUBLIC_PATHS or path.startswith("/api/v1/public")


    return path in _PUBLIC_PATHS or path.startswith("/api/v1/public")

async def auth_middleware(request: Request):
    """Sanic middleware – attaches ``request.ctx.user`` for authenticated routes."""
    # Always allow CORS preflight requests through
    if request.method == "OPTIONS":
        request.ctx.user = None
        return

    if _is_public(request.path):
        request.ctx.user = None
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return sanic_json({"success": False, "message": "Missing or invalid Authorization header"}, status=401)

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return sanic_json({"success": False, "message": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return sanic_json({"success": False, "message": "Invalid token"}, status=401)

    user_id = payload.get("sub")
    if not user_id:
        return sanic_json({"success": False, "message": "Invalid token payload"}, status=401)

    user = await User.select().where(User.id == user_id).first().run()
    if not user:
        return sanic_json({"success": False, "message": "User not found"}, status=401)

    if not user["is_active"]:
        return sanic_json({"success": False, "message": "Account disabled"}, status=403)

    request.ctx.user = user


def require_auth(handler: Callable):
    """Decorator to enforce authentication on a route handler."""

    @wraps(handler)
    async def wrapper(request: Request, *args, **kwargs):
        if not getattr(request.ctx, "user", None):
            return sanic_json({"success": False, "message": "Authentication required"}, status=401)
        return await handler(request, *args, **kwargs)

    return wrapper


def require_admin(handler: Callable):
    """Decorator to enforce admin-only access."""

    @wraps(handler)
    async def wrapper(request: Request, *args, **kwargs):
        user = getattr(request.ctx, "user", None)
        if not user or not user.get("is_admin"):
            return sanic_json({"success": False, "message": "Admin access required"}, status=403)
        return await handler(request, *args, **kwargs)

    return wrapper


def require_tier(*tiers: str):
    """Decorator to restrict access by subscription tier."""

    def decorator(handler: Callable):
        @wraps(handler)
        async def wrapper(request: Request, *args, **kwargs):
            user = getattr(request.ctx, "user", None)
            if not user:
                return sanic_json({"success": False, "message": "Authentication required"}, status=401)
            if user.get("tier", "basic") not in tiers:
                return sanic_json(
                    {"success": False, "message": f"This feature requires one of: {', '.join(tiers)}"},
                    status=403,
                )
            return await handler(request, *args, **kwargs)

        return wrapper

    return decorator
