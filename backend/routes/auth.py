"""
Accura – Authentication Routes
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/verify-email
POST /api/v1/auth/verify-otp
POST /api/v1/auth/resend-otp
GET  /api/v1/auth/check-username/<username>
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
    ResendOTPRequest,
    VerifyEmailRequest,
    VerifyOTPRequest,
)
from services.auth_service import (
    change_password,
    check_username_available,
    login_user,
    refresh_tokens,
    register_user,
    resend_otp,
    verify_email,
    verify_otp,
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

    if user.get("already_exists_unverified"):
        return success(user, message="Account already exists but is not verified. A new verification code has been sent to your email.", status=200)

    return success(user, message="Registration successful. Please check your email for the verification code.", status=201)


@bp.post("/login")
async def login(request: Request):
    try:
        body = LoginRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        tokens = await login_user(email=body.email, password=body.password)
    except (AuthenticationError, ValidationError) as exc:
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


@bp.post("/verify-otp")
async def verify_otp_route(request: Request):
    try:
        body = VerifyOTPRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        await verify_otp(email=body.email, otp=body.otp)
    except (AuthenticationError, ValidationError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Email verified successfully")


@bp.post("/resend-otp")
async def resend_otp_route(request: Request):
    try:
        body = ResendOTPRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    try:
        await resend_otp(email=body.email)
    except (AuthenticationError, ValidationError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Verification code sent")


@bp.get("/check-username/<username:str>")
async def check_username(request: Request, username: str):
    result = await check_username_available(username)
    return success(result)


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
