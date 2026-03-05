"""
Accura – User / Profile Routes
GET    /api/v1/user/me
PUT    /api/v1/user/profile
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from models.user import User, UserProfile
from schemas.user import ProfileUpdateRequest
from utils.responses import error, success

bp = Blueprint("user", url_prefix="/api/v1/user")


@bp.get("/me")
@require_auth
async def get_me(request: Request):
    user = request.ctx.user
    profile = await UserProfile.select().where(
        UserProfile.user == user["id"]
    ).first().run()

    return success({
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "username": user["username"],
            "tier": user["tier"],
            "is_active": user["is_active"],
            "is_verified": user["is_verified"],
            "is_admin": user["is_admin"],
            "created_at": str(user["created_at"]),
        },
        "profile": profile or {},
    })


@bp.put("/profile")
@require_auth
async def update_profile(request: Request):
    try:
        body = ProfileUpdateRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])

    profile = await UserProfile.select().where(
        UserProfile.user == user_id
    ).first().run()

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error("No fields to update", status=422)

    if profile:
        # Explicitly set updated_at to avoid TimestamptzNow issue with SQLite
        updates["updated_at"] = datetime.now(timezone.utc)
        await UserProfile.update(updates).where(
            UserProfile.user == user_id
        ).run()
    else:
        await UserProfile.insert(
            UserProfile(
                id=str(uuid.uuid4()),
                user=user_id,
                **updates,
            )
        ).run()

    updated_profile = await UserProfile.select().where(
        UserProfile.user == user_id
    ).first().run()

    # Re-fetch user data so frontend gets { user, profile }
    user_data = await User.select().where(User.id == user_id).first().run()

    return success(
        {
            "user": {
                "id": str(user_data["id"]),
                "email": user_data["email"],
                "username": user_data["username"],
                "tier": user_data["tier"],
                "is_active": user_data["is_active"],
                "is_verified": user_data["is_verified"],
                "is_admin": user_data["is_admin"],
                "created_at": str(user_data["created_at"]),
            },
            "profile": updated_profile or {},
        },
        message="Profile updated",
    )
