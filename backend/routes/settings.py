"""
Accura – User Settings Routes
GET  /api/v1/settings
PUT  /api/v1/settings
"""

from __future__ import annotations

from datetime import datetime, timezone

from sanic import Blueprint, Request


from middleware.auth_middleware import require_auth
from models.settings import UserSettings
from services.auth_service import new_user_settings
from schemas.settings import UpdateSettingsRequest
from utils.responses import error, success, validation_error
from utils.url_guard import UnsafeURLError, ensure_public_url

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
        await UserSettings.insert(new_user_settings(user_id)).run()
        user_settings = await UserSettings.select().where(
            UserSettings.user == user_id
        ).first().run()

    return success(user_settings)


@bp.put("/")
@require_auth
async def update_settings(request: Request):
    try:
        body = UpdateSettingsRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)
    for url, what in ((body.slack_webhook_url, "Slack webhook URL"), (body.teams_webhook_url, "Teams webhook URL"),):
        if url:
            try:
                await ensure_public_url(url, what=what)
            except UnsafeURLError as exc:
                return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])
    updates = body.model_dump(exclude_none=True)

    if not updates:
        return error("No fields to update", status=422)

    existing = await UserSettings.select().where(
        UserSettings.user == user_id
    ).first().run()

    if existing:
        updates["updated_at"] = datetime.now(timezone.utc)
        await UserSettings.update(updates).where(
            UserSettings.user == user_id
        ).run()
    else:
        await UserSettings.insert(
            new_user_settings(user_id, **updates)
        ).run()

    updated = await UserSettings.select().where(
        UserSettings.user == user_id
    ).first().run()

    return success(updated, message="Settings updated")

