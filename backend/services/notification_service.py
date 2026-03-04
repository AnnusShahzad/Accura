"""
Accura – Notification Dispatch Service
Routes notifications to the appropriate channel(s) based on user preferences.
"""

from __future__ import annotations

import logging
import uuid

from models.notification import Notification
from models.settings import UserSettings
from utils.email import send_email
from utils.webhooks import send_slack_notification, send_teams_notification

logger = logging.getLogger("accura.notification_service")


async def send_notification(
    user_id: str,
    title: str,
    body: str,
    *,
    channels: list[str] | None = None,
    metadata: dict | None = None,
) -> list[str]:
    """Dispatch a notification to all enabled channels for the user.

    Returns a list of channel names that were dispatched.
    """
    dispatched: list[str] = []

    # Load user settings for notification preferences
    user_settings = await UserSettings.select().where(
        UserSettings.user == user_id
    ).first().run()

    if not user_settings or not user_settings.get("notifications_enabled", True):
        return dispatched

    target_channels = channels or []
    if not target_channels:
        # Use user preferences
        if user_settings.get("notify_in_app", True):
            target_channels.append("in_app")
        if user_settings.get("notify_email", False):
            target_channels.append("email")
        if user_settings.get("notify_slack", False):
            target_channels.append("slack")
        if user_settings.get("notify_teams", False):
            target_channels.append("teams")

    for channel in target_channels:
        try:
            if channel == "in_app":
                await _dispatch_in_app(user_id, title, body, metadata)
                dispatched.append("in_app")

            elif channel == "email":
                from models.user import User
                user = await User.select(User.email).where(User.id == user_id).first().run()
                if user:
                    await send_email(
                        to=user["email"],
                        subject=title,
                        text_body=body,
                    )
                    dispatched.append("email")

            elif channel == "slack":
                webhook_url = user_settings.get("slack_webhook_url", "")
                if webhook_url:
                    await send_slack_notification(webhook_url, f"*{title}*\n{body}")
                    dispatched.append("slack")

            elif channel == "teams":
                webhook_url = user_settings.get("teams_webhook_url", "")
                if webhook_url:
                    await send_teams_notification(webhook_url, title, body)
                    dispatched.append("teams")

        except Exception:
            logger.exception("Failed to dispatch %s notification to user %s", channel, user_id)

    return dispatched


async def _dispatch_in_app(user_id: str, title: str, body: str, metadata: dict | None) -> None:
    """Store an in-app notification record."""
    await Notification.insert(
        Notification(
            id=str(uuid.uuid4()),
            user=user_id,
            channel="in_app",
            title=title,
            body=body,
            metadata=metadata or {},
        )
    ).run()


async def get_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch in-app notifications for a user."""
    query = Notification.select().where(
        (Notification.user == user_id) & (Notification.channel == "in_app")
    )
    if unread_only:
        query = query.where(Notification.is_read == False)
    return await query.order_by(Notification.created_at, ascending=False).limit(limit).offset(offset).run()


async def mark_as_read(notification_id: str, user_id: str) -> bool:
    await Notification.update({Notification.is_read: True}).where(
        (Notification.id == notification_id) & (Notification.user == user_id)
    ).run()
    return True
