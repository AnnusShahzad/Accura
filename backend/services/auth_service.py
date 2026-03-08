"""
Accura – Authentication Service
Handles registration, login, JWT token generation, password hashing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config import settings
from models.user import User, UserProfile
from models.settings import UserSettings
from utils.email import send_email
from utils.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger("accura.auth_service")

_JWT_SECRET: str = settings.get("jwt.secret", "changeme")
_JWT_ALGORITHM: str = settings.get("jwt.algorithm", "HS256")
_ACCESS_EXPIRE: int = settings.get("jwt.access_token_expire_minutes", 30)
_REFRESH_EXPIRE: int = settings.get("jwt.refresh_token_expire_days", 30)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_EXPIRE),
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

    # Check uniqueness
    existing = await User.select(User.id).where(
        (User.email == email) | (User.username == username)
    ).first().run()
    if existing:
        raise ValidationError("Email or username already taken")

    user_id = str(uuid.uuid4())
    hashed = hash_password(password)

    await User.insert(
        User(
            id=user_id,
            email=email,
            username=username,
            hashed_password=hashed,
            tier="basic",
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
    await UserSettings.insert(
        UserSettings(
            id=str(uuid.uuid4()),
            user=user_id,
        )
    ).run()

    # Send verification email (fire-and-forget; log errors)
    try:
        verification_token = create_access_token(user_id, extra={"type": "verify_email"})
        await send_email(
            to=email,
            subject="Verify your Accura account",
            template_name="verify_email.html",
            template_context={
                "username": username,
                "verification_url": f"{settings.get('app.frontend_url', '')}/verify?token={verification_token}",
            },
        )
    except Exception:
        logger.warning("Verification email could not be sent to %s", email)

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

    access = create_access_token(str(user["id"]), extra={"tier": user["tier"]})
    refresh = create_refresh_token(str(user["id"]))

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": _ACCESS_EXPIRE * 60,
    }


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

    access = create_access_token(str(user["id"]), extra={"tier": user["tier"]})
    refresh = create_refresh_token(str(user["id"]))

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": _ACCESS_EXPIRE * 60,
    }


# ---------------------------------------------------------------------------
# Verify email
# ---------------------------------------------------------------------------

async def verify_email(token: str) -> bool:
    payload = decode_token(token)
    if payload.get("type") != "verify_email":
        raise AuthenticationError("Invalid verification token")

    user_id = payload["sub"]
    await User.update({User.is_verified: True}).where(User.id == user_id).run()
    return True

# ---------------------------------------------------------------------------
# Request password fun
# ---------------------------------------------------------------------------

async def request_password_reset(email: str) -> bool:

    user = await User.select().where(User.email == email).first().run()

    # Security: don't reveal if email exists
    if not user:
        return True

    user_id = str(user["id"])

    reset_token = create_access_token(
        user_id,
        extra={"type": "password_reset"}
    )

    reset_url = f"{settings.get('app.frontend_url','')}/reset-password?token={reset_token}"

    await send_email(
        to=user["email"],
        subject="Reset your Accura password",
        template_name="reset_password.html",
        template_context={
            "username": user["username"],
            "reset_url": reset_url,
        },
    )

    return True

# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

async def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    user = await User.select().where(User.id == user_id).first().run()
    if not user:
        raise AuthenticationError("User not found")

    if not verify_password(old_password, user["hashed_password"]):
        raise AuthenticationError("Current password is incorrect")

    hashed = hash_password(new_password)
    await User.update({User.hashed_password: hashed}).where(User.id == user_id).run()
    return True

# ---------------------------------------------------------------------------
# Reset password fun
# ---------------------------------------------------------------------------

async def reset_password(token: str, new_password: str) -> bool:

    payload = decode_token(token)

    if payload.get("type") != "password_reset":
        raise AuthenticationError("Invalid reset token")

    user_id = payload["sub"]

    hashed = hash_password(new_password)

    await User.update(
        {User.hashed_password: hashed}
    ).where(
        User.id == user_id
    ).run()

    return True

async def request_email_change(user_id: str, new_email: str) -> bool:
    from models.user import User
    from utils.email import send_email
    from config import settings

    existing = await User.select().where(User.email == new_email).first().run()
    if existing:
        raise ValidationError("Email already in use")

    token = create_access_token(
        user_id,
        extra={
            "type": "email_change",
            "new_email": new_email,
        },
    )

    verify_url = f"{settings.get('app.frontend_url','')}/email-change?token={token}"

    user = await User.select().where(User.id == user_id).first().run()

    await send_email(
        to=new_email,
        subject="Confirm your new email",
        template_name="verify_email.html",
        template_context={
            "username": user["username"],
            "verification_url": verify_url,
        },
    )

    return True

async def confirm_email_change(token: str) -> bool:

    payload = decode_token(token)

    print("TOKEN PAYLOAD:", payload)

    if payload.get("type") != "email_change":
        raise AuthenticationError("Invalid email change token")

    user_id = payload["sub"]
    new_email = payload["new_email"]

    print("Updating user:", user_id)
    print("New email:", new_email)

    await User.update(
        {User.email: new_email}
    ).where(
        User.id == user_id
    ).run()

    print("EMAIL UPDATED")

    return True