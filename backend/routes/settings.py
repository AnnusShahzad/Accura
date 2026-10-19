"""
Accura – User Settings Routes
GET  /api/v1/settings
PUT  /api/v1/settings
"""

from __future__ import annotations

import uuid

from sanic import Blueprint, Request


from middleware.auth_middleware import require_auth
from models.settings import UserSettings
from schemas.settings import UpdateSettingsRequest
from utils.responses import error, success, validation_error

bp = Blueprint("settings", url_prefix="/api/v1/settings")


@bp.get("/")
@require_auth
async def get_settings(request: Request):
    user_id = str(request.ctx.user["id"])

    user_settings = await UserSettings.select().where(
        UserSettings.user == user_id
    ).first().run()

    if not user_settings:
        # Create defaults
        settings_id = str(uuid.uuid4())
        await UserSettings.insert(
            UserSettings(id=settings_id, user=user_id)
        ).run()
        user_settings = await UserSettings.select().where(
            UserSettings.id == settings_id
        ).first().run()

    return success(user_settings)


@bp.put("/")
@require_auth
async def update_settings(request: Request):
    try:
        body = UpdateSettingsRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])
    updates = body.model_dump(exclude_none=True)

    if not updates:
        return error("No fields to update", status=422)

    existing = await UserSettings.select().where(
        UserSettings.user == user_id
    ).first().run()

    if existing:
        await UserSettings.update(updates).where(
            UserSettings.user == user_id
        ).run()
    else:
        await UserSettings.insert(
            UserSettings(id=str(uuid.uuid4()), user=user_id, **updates)
        ).run()

    updated = await UserSettings.select().where(
        UserSettings.user == user_id
    ).first().run()

    return success(updated, message="Settings updated")

