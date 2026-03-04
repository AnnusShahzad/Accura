"""
Accura – Notification Routes
GET    /api/v1/notifications
PATCH  /api/v1/notifications/<id>/read
"""

from __future__ import annotations

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from services.notification_service import get_notifications, mark_as_read
from utils.responses import success

bp = Blueprint("notifications", url_prefix="/api/v1/notifications")


@bp.get("/")
@require_auth
async def list_notifications(request: Request):
    user_id = str(request.ctx.user["id"])
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))

    notifications = await get_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return success(notifications)


@bp.patch("/<notification_id:str>/read")
@require_auth
async def read_notification(request: Request, notification_id: str):
    user_id = str(request.ctx.user["id"])
    await mark_as_read(notification_id, user_id)
    return success(message="Notification marked as read")
