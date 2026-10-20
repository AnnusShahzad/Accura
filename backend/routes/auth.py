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
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
POST /api/v1/auth/request-email-change
POST /api/v1/auth/verify-email-change
"""

from __future__ import annotations

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from schemas.auth import (
    ChangePasswordRequest,
    EmailChangeRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    TokenRequest,
    VerifyEmailRequest,
    VerifyOTPRequest,
)
from services.auth_service import (
    change_password,
    check_username_available,
    confirm_email_change,
    login_user,
    refresh_tokens,
    register_user,
    request_email_change,
    request_password_reset,
    resend_otp,
    reset_password,
    verify_email,
    verify_otp,
)
from utils.exceptions import AuthenticationError, ValidationError
from utils.responses import error, success, validation_error

bp = Blueprint("auth", url_prefix="/api/v1/auth")


@bp.post("/register")
async def register(request: Request):
    try:
        body = RegisterRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

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
        body = LoginRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        tokens = await login_user(email=body.email, password=body.password)
    except (AuthenticationError, ValidationError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(tokens, message="Login successful")


@bp.post("/refresh")
async def refresh(request: Request):
    try:
        body = RefreshRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        tokens = await refresh_tokens(body.refresh_token)
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(tokens, message="Tokens refreshed")


@bp.post("/verify-email")
async def verify(request: Request):
    try:
        body = VerifyEmailRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        await verify_email(body.token)
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Email verified")

@bp.post("/forgot-password")
async def forgot_password(request: Request):
    try:
        body = ForgotPasswordRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    await request_password_reset(body.email)
    return success(message="If the email exists, a reset link has been sent.")


@bp.post("/reset-password")
async def reset_pwd(request: Request):
    try:
        body = ResetPasswordRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        await reset_password(body.token, body.new_password)
    except (AuthenticationError, ValidationError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Password reset successful")


@bp.post("/verify-otp")
async def verify_otp_route(request: Request):
    try:
        body = VerifyOTPRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        await verify_otp(email=body.email, otp=body.otp)
    except (AuthenticationError, ValidationError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Email verified successfully")


@bp.post("/resend-otp")
async def resend_otp_route(request: Request):
    try:
        body = ResendOTPRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

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
        body = ChangePasswordRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        await change_password(
            user_id=str(request.ctx.user["id"]),
            old_password=body.old_password,
            new_password=body.new_password,
        )
    except (AuthenticationError, ValidationError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Password changed")

@bp.post("/request-email-change")
@require_auth
async def request_email_change_route(request: Request):
    try:
        body = EmailChangeRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        await request_email_change(
            user_id=str(request.ctx.user["id"]),
            new_email=body.email,
        )
    except (AuthenticationError, ValidationError) as exc:
        return error(exc.message, status=exc.status_code)

    return success(message="Verification email sent")


@bp.post("/verify-email-change")
async def verify_email_change_route(request: Request):
    try:
        body = TokenRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    try:
        new_email = await confirm_email_change(body.token)
    except AuthenticationError as exc:
        return error(exc.message, status=exc.status_code)

    return success({"email": new_email}, message="Email updated")
