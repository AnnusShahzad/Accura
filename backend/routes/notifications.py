"""
Accura – Notification Routes
GET    /api/v1/notifications
PATCH  /api/v1/notifications/<id>/read
PATCH  /api/v1/notifications/read-all
"""

from __future__ import annotations

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from models.notification import Notification
from services.notification_service import get_notifications, mark_as_read
from utils.responses import success, int_arg

bp = Blueprint("notifications", url_prefix="/api/v1/notifications")


@bp.get("/")
@require_auth
async def list_notifications(request: Request):
    user_id = str(request.ctx.user["id"])
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = int_arg(request, "limit", 50, minimum=1, maximum=100)
    offset = int_arg(request, "offset", 0)

    notifications = await get_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return success(notifications)


@bp.patch("/read-all")
@require_auth
async def read_all_notifications(request: Request):
    """Mark all in-app notifications as read for this user."""
    user_id = str(request.ctx.user["id"])
    await Notification.update({Notification.is_read: True}).where(
        (Notification.user == user_id) & (Notification.is_read == False)
    ).run()
    return success(message="All notifications marked as read")


@bp.patch("/<notification_id:str>/read")
@require_auth
async def read_notification(request: Request, notification_id: str):
    user_id = str(request.ctx.user["id"])
    await mark_as_read(notification_id, user_id)
    return success(message="Notification marked as read")
