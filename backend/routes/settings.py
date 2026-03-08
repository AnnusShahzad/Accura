"""
Accura – User Settings Routes
GET  /api/v1/settings
PUT  /api/v1/settings
"""

from __future__ import annotations

import uuid

from sanic import Blueprint, Request

# from utils.exceptions import AuthenticationError, ValidationError

from middleware.auth_middleware import require_auth
from models.settings import UserSettings
from schemas.settings import UpdateSettingsRequest
from utils.responses import error, success
# from services.auth_service import request_email_change, confirm_email_change

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
        body = UpdateSettingsRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

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

# @bp.post("/request-email-change")
# @require_auth
# async def request_email_change_route(request: Request):

#     new_email = request.json.get("email")

#     if not new_email:
#         return error("Email is required", status=422)

#     try:
#         await request_email_change(
#             user_id=str(request.ctx.user["id"]),
#             new_email=new_email,
#         )
#     except ValidationError as exc:
#         return error(exc.message, status=exc.status_code)

#     return success(message="Verification email sent")

# @bp.post("/verify-email-change")
# async def verify_email_change(request: Request):

#     token = request.json.get("token")

#     if not token:
#         return error("Token required", status=422)

#     try:
#         await confirm_email_change(token)
#     except AuthenticationError as exc:
#         return error(exc.message, status=exc.status_code)

#     return success(message="Email updated successfully")