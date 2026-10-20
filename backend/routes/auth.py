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
POST /api/v1/auth/guest
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

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
    create_guest,
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
from utils.exceptions import AuthenticationError, AuthorizationError, ValidationError
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
    except (ValidationError, AuthorizationError) as exc:
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
    except (AuthenticationError, AuthorizationError, ValidationError) as exc:
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
    except (AuthenticationError, AuthorizationError, ValidationError) as exc:
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



# Guest sign-ins per client IP, to stop scripts minting accounts that all
# spend the platform's AI budget.
_GUEST_WINDOW_SECONDS = 3600
_GUESTS_PER_WINDOW = 5
_guest_signins: dict[str, deque] = defaultdict(deque)
# X-Forwarded-For can be forged, so the per-IP limit alone can be dodged;
# a site-wide hourly cap bounds the total no matter what clients claim.
_all_guest_signins: deque = deque()


def _client_ip(request: Request) -> str:
    # Render, Vercel, Fly etc. put the real client first in X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or request.ip or "unknown"


@bp.post("/guest")
async def guest_login(request: Request):
    ip = _client_ip(request)
    now = time.monotonic()
    recent = _guest_signins[ip]
    while recent and now - recent[0] > _GUEST_WINDOW_SECONDS:
        recent.popleft()
    if len(recent) >= _GUESTS_PER_WINDOW:
        return error(
            "Too many guest sessions from your network. Please try again later.",
            status=429,
            retry_after_seconds=_GUEST_WINDOW_SECONDS,
        )
    while _all_guest_signins and now - _all_guest_signins[0] > _GUEST_WINDOW_SECONDS:
        _all_guest_signins.popleft()
    from config import settings

    if len(_all_guest_signins) >= int(settings.get("auth.guest.signups_per_hour", 60)):
        return error(
            "Guest access is very busy right now. Please try again in a little while.",
            status=429,
            retry_after_seconds=600,
        )

    try:
        tokens = await create_guest()
    except AuthorizationError as exc:
        return error(exc.message, status=exc.status_code)

    recent.append(now)
    _all_guest_signins.append(now)
    return success(tokens, message="Guest session started", status=201)
