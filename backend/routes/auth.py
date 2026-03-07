"""
Accura – Authentication Routes
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/verify-email
POST /api/v1/auth/change-password
"""

from __future__ import annotations

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    VerifyEmailRequest,
)
from services.auth_service import (
    change_password,
    login_user,
    refresh_tokens,
    register_user,
    verify_email,
)
from services.auth_service import (
    change_password,
    login_user,
    refresh_tokens,
    register_user,
    verify_email,
    request_password_reset,
    reset_password,
)
from utils.exceptions import AuthenticationError, ValidationError
from utils.responses import error, success

bp = Blueprint("auth", url_prefix="/api/v1/auth")


@bp.post("/register")
async def register(request: Request):
    try:
        body = RegisterRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        user = await register_user(
            email=body.email,
            username=body.username,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
        )
    except ValidationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(user, message="Registration successful", status=201)


@bp.post("/login")
async def login(request: Request):
    try:
        body = LoginRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        tokens = await login_user(email=body.email, password=body.password)
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(tokens, message="Login successful")


@bp.post("/refresh")
async def refresh(request: Request):
    try:
        body = RefreshRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        tokens = await refresh_tokens(body.refresh_token)
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(tokens, message="Tokens refreshed")


@bp.post("/verify-email")
async def verify(request: Request):
    try:
        body = VerifyEmailRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        await verify_email(body.token)
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Email verified")

@bp.post("/forgot-password")
async def forgot_password(request: Request):

    email = request.json.get("email")

    if not email:
        return error("Email is required", status=422)

    await request_password_reset(email)

    return success(message="If the email exists, a reset link has been sent.")

@bp.post("/reset-password")
async def reset_pwd(request: Request):

    token = request.json.get("token")
    new_password = request.json.get("new_password")

    if not token or not new_password:
        return error("Token and new password are required", status=422)

    try:
        await reset_password(token, new_password)
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Password reset successful")

@bp.post("/change-password")
@require_auth
async def change_pwd(request: Request):
    try:
        body = ChangePasswordRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        await change_password(
            user_id=str(request.ctx.user["id"]),
            old_password=body.old_password,
            new_password=body.new_password,
        )
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Password changed")
