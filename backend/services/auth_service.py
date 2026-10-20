"""
Accura – Authentication Service
Handles registration, login, JWT token generation, password hashing, OTP verification.
"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config import settings
from models.user import User, UserProfile
from models.settings import UserSettings
from utils.email import send_email
from utils.exceptions import AuthenticationError, AuthorizationError, ValidationError

logger = logging.getLogger("accura.auth_service")

_JWT_SECRET: str = settings.get("jwt.secret", "changeme")
_JWT_ALGORITHM: str = settings.get("jwt.algorithm", "HS256")
_ACCESS_EXPIRE: int = settings.get("jwt.access_token_expire_minutes", 30)
_REFRESH_EXPIRE: int = settings.get("jwt.refresh_token_expire_days", 30)
_OTP_EXPIRE_MINUTES: int = 60
_RESET_EXPIRE_MINUTES: int = 30
_EMAIL_CHANGE_EXPIRE_MINUTES: int = 60


def _log_otp(email: str, otp_code: str) -> None:
    """Log OTP codes only in debug mode so they never leak into prod logs."""
    if settings.get("app.debug", False):
        logger.info("OTP for %s: %s (debug mode only)", email, otp_code)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_password(password: str) -> None:
    """Enforce military-grade password requirements."""
    errors = []
    if len(password) <= 8:
        errors.append("Password must be greater than 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least 1 uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least 1 lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("Password must contain at least 1 number")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
        errors.append("Password must contain at least 1 special character")
    if errors:
        raise ValidationError("; ".join(errors))


def validate_username(username: str) -> None:
    """Enforce username requirements."""
    if len(username) < 5:
        raise ValidationError("Username must be at least 5 characters")
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise ValidationError(
            "Username can only contain letters, numbers, and underscores"
        )


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------

def generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return f"{secrets.randbelow(1_000_000):06d}"


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str, extra: dict | None = None, expire_minutes: int | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes or _ACCESS_EXPIRE),
        "type": "access",
        **(extra or {}),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=_REFRESH_EXPIRE),
        "type": "refresh",
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


def token_pair(user: dict) -> dict:
    return {
        "access_token": create_access_token(str(user["id"]), extra={"tier": user["tier"]}),
        "refresh_token": create_refresh_token(str(user["id"])),
        "token_type": "bearer",
        "expires_in": _ACCESS_EXPIRE * 60,
    }


def guest_expired(user: dict) -> bool:
    expires_at = user.get("expires_at")
    if not user.get("is_guest") or not expires_at:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= expires_at


def ensure_not_guest(user: dict | None, action: str) -> None:
    if user and user.get("is_guest"):
        raise AuthorizationError(f"Guest accounts can't {action}.")


def new_user_settings(user_id: str, **overrides) -> UserSettings:
    """Settings row for a new user, preferring the server's default models
    (so a deployment that only has, say, an OpenRouter key works out of
    the box) over the column defaults."""
    values = {
        "preferred_generator_model": settings.get("ai.default_generator_model") or "gpt-5.2",
        "preferred_evaluator_model": settings.get("ai.default_evaluator_model") or "gpt-5.1",
        "preferred_critic_model": settings.get("ai.default_evaluator_model") or "gpt-5.1",
        **overrides,
    }
    return UserSettings(id=str(uuid.uuid4()), user=user_id, **values)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def register_user(
    email: str,
    username: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
) -> dict:
    """Create a new user account with default settings and profile."""

    if not settings.get("auth.registration_enabled", True):
        raise AuthorizationError(
            "Registration is closed on this server. You can try Accura with a guest account instead."
        )

    # Validate username and password on server side
    validate_username(username)
    validate_password(password)

    # Check email uniqueness
    existing_user = await User.select().where(
        User.email == email
    ).first().run()
    
    if existing_user:
        if not existing_user["is_verified"]:
            # User exists but isn't verified. Generate new OTP and resend.
            otp_code = generate_otp()
            otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=_OTP_EXPIRE_MINUTES)
            
            await User.update({
                User.otp_code: otp_code,
                User.otp_expires_at: otp_expires_at
            }).where(User.id == existing_user["id"]).run()
            
            # Send OTP email
            try:
                _log_otp(email, otp_code)
                await send_email(
                    to=email,
                    subject="Your Accura Verification Code",
                    template_name="otp_email.html",
                    template_context={
                        "username": existing_user["username"],
                        "otp_code": otp_code,
                        "expire_minutes": _OTP_EXPIRE_MINUTES,
                    },
                )
            except Exception as e:
                logger.warning("OTP email could not be sent to %s: %s", email, e)
            
            return {
                "id": str(existing_user["id"]), 
                "email": email, 
                "username": existing_user["username"], 
                "tier": existing_user["tier"],
                "already_exists_unverified": True
            }
        else:
            raise ValidationError("Email is already taken")

    # Check username uniqueness
    existing_username = await User.select(User.id).where(
        User.username == username
    ).first().run()
    if existing_username:
        raise ValidationError("Username is already taken")

    user_id = str(uuid.uuid4())
    hashed = hash_password(password)
    otp_code = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=_OTP_EXPIRE_MINUTES)

    await User.insert(
        User(
            id=user_id,
            email=email,
            username=username,
            hashed_password=hashed,
            tier="basic",
            otp_code=otp_code,
            otp_expires_at=otp_expires_at,
        )
    ).run()

    # Create profile
    await UserProfile.insert(
        UserProfile(
            id=str(uuid.uuid4()),
            user=user_id,
            first_name=first_name,
            last_name=last_name,
        )
    ).run()

    # Create default settings
    await UserSettings.insert(new_user_settings(user_id)).run()

    # Send OTP verification email
    try:
        _log_otp(email, otp_code)
        await send_email(
            to=email,
            subject="Your Accura Verification Code",
            template_name="otp_email.html",
            template_context={
                "username": username,
                "otp_code": otp_code,
                "expire_minutes": _OTP_EXPIRE_MINUTES,
            },
        )
    except Exception as e:
        logger.warning("OTP email could not be sent to %s: %s", email, e)

    return {"id": user_id, "email": email, "username": username, "tier": "basic"}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def login_user(email: str, password: str) -> dict:
    """Authenticate user and return token pair."""

    user = await User.select().where(User.email == email).first().run()
    if not user:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user["hashed_password"]):
        raise AuthenticationError("Invalid email or password")

    if not user["is_active"]:
        raise AuthenticationError("Account is disabled")

    if not user["is_verified"]:
        # Generate new OTP and send email so they have it immediately upon redirect
        otp_code = generate_otp()
        otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=_OTP_EXPIRE_MINUTES)
        
        await User.update({
            User.otp_code: otp_code,
            User.otp_expires_at: otp_expires_at
        }).where(User.id == user["id"]).run()
        
        try:
            _log_otp(email, otp_code)
            await send_email(
                to=email,
                subject="Your Accura Verification Code",
                template_name="otp_email.html",
                template_context={
                    "username": user["username"],
                    "otp_code": otp_code,
                    "expire_minutes": _OTP_EXPIRE_MINUTES,
                },
            )
        except Exception as e:
            logger.warning("Auto-OTP email could not be sent to %s: %s", email, e)

        raise ValidationError(
            "Please verify your email before logging in. A new verification code has been sent to your inbox.",
            status_code=403
        )

    return token_pair(user)


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

async def refresh_tokens(refresh_token: str) -> dict:
    """Validate refresh token and issue new token pair."""

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token")

    user_id = payload["sub"]
    user = await User.select().where(User.id == user_id).first().run()
    if not user or not user["is_active"]:
        raise AuthenticationError("User not found or deactivated")
    if guest_expired(user):
        raise AuthenticationError("This guest session has ended")

    return token_pair(user)


# ---------------------------------------------------------------------------
# Verify email (link-based — kept for backward compat)
# ---------------------------------------------------------------------------

async def verify_email(token: str) -> bool:
    payload = decode_token(token)
    if payload.get("type") != "verify_email":
        raise AuthenticationError("Invalid verification token")

    user_id = payload["sub"]
    await User.update({User.is_verified: True}).where(User.id == user_id).run()
    return True

# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def _password_fingerprint(hashed_password: str) -> str:
    """Short digest of the current hash; changes whenever the password does.

    Embedding it in reset tokens makes each link single-use: once the
    password is reset, every previously issued link stops validating.
    """
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


async def request_password_reset(email: str) -> bool:
    user = await User.select().where(User.email == email).first().run()

    # Security: don't reveal if email exists
    if not user:
        return True

    reset_token = create_access_token(
        str(user["id"]),
        extra={
            "type": "password_reset",
            "pwd": _password_fingerprint(user["hashed_password"]),
        },
        expire_minutes=_RESET_EXPIRE_MINUTES,
    )

    reset_url = f"{settings.get('app.frontend_url', '')}/reset-password?token={reset_token}"

    try:
        await send_email(
            to=user["email"],
            subject="Reset your Accura password",
            template_name="reset_password.html",
            template_context={
                "username": user["username"],
                "reset_url": reset_url,
                "expire_minutes": _RESET_EXPIRE_MINUTES,
            },
        )
    except Exception as e:
        # Still answer generically so the endpoint can't be used to probe
        # which addresses are registered.
        logger.warning("Password reset email could not be sent to %s: %s", email, e)
        if settings.get("app.debug", False):
            logger.info("Password reset link for %s: %s (debug mode only)", email, reset_url)

    return True

# ---------------------------------------------------------------------------
# Verify OTP
# ---------------------------------------------------------------------------

async def verify_otp(email: str, otp: str) -> bool:
    """Verify the 6-digit OTP code for email verification."""
    user = await User.select().where(User.email == email).first().run()
    if not user:
        raise AuthenticationError("User not found")

    if user["is_verified"]:
        raise ValidationError("Email is already verified")

    if user["otp_code"] != otp:
        raise AuthenticationError("Invalid OTP code")

    # Check expiry
    otp_expires = user["otp_expires_at"]
    if otp_expires:
        # Ensure we compare timezone-aware datetimes correctly
        if otp_expires.tzinfo is None:
            otp_expires = otp_expires.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > otp_expires:
            raise AuthenticationError("OTP has expired. Please request a new one.")

    # Mark verified and clear OTP
    await User.update({
        User.is_verified: True,
        User.otp_code: "",
        User.otp_expires_at: None,
    }).where(User.id == user["id"]).run()

    return True


# ---------------------------------------------------------------------------
# Resend OTP
# ---------------------------------------------------------------------------

async def resend_otp(email: str) -> bool:
    """Generate and send a new OTP to the user's email."""
    user = await User.select().where(User.email == email).first().run()
    if not user:
        raise AuthenticationError("User not found")

    if user["is_verified"]:
        raise ValidationError("Email is already verified")

    otp_code = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=_OTP_EXPIRE_MINUTES)

    await User.update({
        User.otp_code: otp_code,
        User.otp_expires_at: otp_expires_at,
    }).where(User.id == user["id"]).run()

    try:
        _log_otp(email, otp_code)
        await send_email(
            to=email,
            subject="Your Accura Verification Code",
            template_name="otp_email.html",
            template_context={
                "username": user["username"],
                "otp_code": otp_code,
                "expire_minutes": _OTP_EXPIRE_MINUTES,
            },
        )
    except Exception as e:
        logger.warning("OTP resend email could not be sent to %s: %s", email, e)
        raise ValidationError("Failed to send verification email. Check SMTP settings.", status_code=500)

    return True


# ---------------------------------------------------------------------------
# Check username availability
# ---------------------------------------------------------------------------

async def check_username_available(username: str) -> dict:
    """Check if a username is available."""
    # Validate format first
    try:
        validate_username(username)
    except ValidationError as e:
        return {"available": False, "message": e.message}

    existing = await User.select(User.id).where(
        User.username == username
    ).first().run()

    if existing:
        return {"available": False, "message": "Username is already taken"}

    return {"available": True, "message": "Username is available"}

# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

async def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    user = await User.select().where(User.id == user_id).first().run()
    if not user:
        raise AuthenticationError("User not found")
    ensure_not_guest(user, "change their password")

    if not verify_password(old_password, user["hashed_password"]):
        raise AuthenticationError("Current password is incorrect")

    # Validate new password strength
    validate_password(new_password)

    hashed = hash_password(new_password)
    await User.update({
        User.hashed_password: hashed,
        User.updated_at: datetime.now(timezone.utc),
    }).where(User.id == user_id).run()
    return True

# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------

async def reset_password(token: str, new_password: str) -> bool:
    payload = decode_token(token)
    if payload.get("type") != "password_reset":
        raise AuthenticationError("Invalid reset token")

    user = await User.select().where(User.id == payload["sub"]).first().run()
    if not user or payload.get("pwd") != _password_fingerprint(user["hashed_password"]):
        raise AuthenticationError("This reset link has already been used or is invalid")

    validate_password(new_password)

    await User.update({
        User.hashed_password: hash_password(new_password),
        User.updated_at: datetime.now(timezone.utc),
    }).where(User.id == user["id"]).run()
    return True


# ---------------------------------------------------------------------------
# Email change
# ---------------------------------------------------------------------------

async def request_email_change(user_id: str, new_email: str) -> bool:
    new_email = new_email.strip().lower()
    existing = await User.select(User.id).where(User.email == new_email).first().run()
    if existing:
        raise ValidationError("Email already in use")

    user = await User.select().where(User.id == user_id).first().run()
    if not user:
        raise AuthenticationError("User not found")
    ensure_not_guest(user, "change their email address")

    token = create_access_token(
        user_id,
        extra={"type": "email_change", "new_email": new_email},
        expire_minutes=_EMAIL_CHANGE_EXPIRE_MINUTES,
    )
    verify_url = f"{settings.get('app.frontend_url', '')}/email-change?token={token}"

    try:
        await send_email(
            to=new_email,
            subject="Confirm your new email",
            template_name="verify_email.html",
            template_context={
                "username": user["username"],
                "verification_url": verify_url,
            },
        )
    except Exception as e:
        logger.warning("Email change confirmation could not be sent to %s: %s", new_email, e)
        raise ValidationError("Failed to send confirmation email. Check SMTP settings.", status_code=500)

    return True


async def confirm_email_change(token: str) -> str:
    payload = decode_token(token)
    if payload.get("type") != "email_change" or not payload.get("new_email"):
        raise AuthenticationError("Invalid email change token")

    user_id = payload["sub"]
    new_email = payload["new_email"]

    # The address may have been claimed between request and confirmation.
    taken = await User.select(User.id).where(
        (User.email == new_email) & (User.id != user_id)
    ).first().run()
    if taken:
        raise AuthenticationError("That email address is already in use")

    await User.update({
        User.email: new_email,
        User.is_verified: True,
        User.updated_at: datetime.now(timezone.utc),
    }).where(User.id == user_id).run()

    logger.info("User %s changed email to %s", user_id, new_email)
    return new_email


# ---------------------------------------------------------------------------
# Guest accounts
# ---------------------------------------------------------------------------

async def create_guest() -> dict:
    """Create a throwaway, already-verified account and log it in."""
    if not settings.get("auth.guest.enabled", False):
        raise AuthorizationError("Guest access is not enabled on this server")

    ttl_hours = int(settings.get("auth.guest.ttl_hours", 24))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    suffix = secrets.token_hex(5)
    user_id = str(uuid.uuid4())

    user = {
        "id": user_id,
        "email": f"guest-{suffix}@guest.accura.invalid",
        "username": f"guest_{suffix}",
        "tier": "basic",
    }
    await User.insert(
        User(
            **user,
            # Nobody knows this password; guests only ever use their tokens
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            is_verified=True,
            is_guest=True,
            expires_at=expires_at,
        )
    ).run()
    await UserProfile.insert(
        UserProfile(id=str(uuid.uuid4()), user=user_id, first_name="Guest")
    ).run()
    cap = int(settings.get("auth.guest.max_iterations", 3))
    await UserSettings.insert(new_user_settings(user_id, max_iterations=min(5, cap))).run()

    logger.info("Created guest account %s (expires %s)", user["username"], expires_at.isoformat())
    return {**token_pair(user), "expires_at": expires_at.isoformat()}


# ---------------------------------------------------------------------------
# Bootstrap admin
# ---------------------------------------------------------------------------

async def ensure_bootstrap_admin() -> None:
    """Create or promote the admin named by ADMIN_EMAIL / ADMIN_PASSWORD.

    Hosts like Render's free tier have no shell, so create_admin.py can't
    be run there. Re-applying the password on every start also gives the
    operator a way to reset it.
    """
    email = (settings.get("auth.bootstrap_admin.email") or "").strip().lower()
    password = settings.get("auth.bootstrap_admin.password") or ""
    if not email or not password:
        return
    try:
        validate_password(password)
    except ValidationError as exc:
        logger.error("ADMIN_PASSWORD rejected, bootstrap admin not created: %s", exc.message)
        return

    user = await User.select().where(User.email == email).first().run()
    if user:
        updates = {User.is_admin: True, User.is_verified: True, User.is_active: True}
        if not verify_password(password, user["hashed_password"]):
            updates[User.hashed_password] = hash_password(password)
        await User.update(updates).where(User.id == user["id"]).run()
        return

    username = (settings.get("auth.bootstrap_admin.username") or "").strip()
    if not username:
        username = re.sub(r"[^a-zA-Z0-9_]", "_", email.split("@")[0])
    username = (username + "_admin")[:150] if len(username) < 5 else username[:150]
    if await User.select(User.id).where(User.username == username).first().run():
        username = f"{username}_{secrets.token_hex(3)}"

    user_id = str(uuid.uuid4())
    await User.insert(
        User(
            id=user_id,
            email=email,
            username=username,
            hashed_password=hash_password(password),
            is_admin=True,
            is_verified=True,
        )
    ).run()
    await UserProfile.insert(UserProfile(id=str(uuid.uuid4()), user=user_id)).run()
    await UserSettings.insert(new_user_settings(user_id)).run()
    logger.info("Created bootstrap admin %s", email)
