"""
Accura – Notification Models
"""

from piccolo.columns import (
    UUID,
    Boolean,
    Text,
    Timestamptz,
    Varchar,
    JSONB,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from models.base import JSONTable

from models.user import User


class Notification(JSONTable, tablename="notifications"):
    """Individual notification record."""

    id = UUID(primary_key=True)
    user = UUID(references=User, index=True)
    channel = Varchar(length=20, default="in_app")  # in_app | email | slack | teams
    title = Varchar(length=500, default="")
    body = Text(default="")
    is_read = Boolean(default=False)
    metadata = JSONB(default={})
    created_at = Timestamptz(default=TimestamptzNow())


class NotificationPreference(Table, tablename="notification_preferences"):
    """Per-user notification channel preferences (mirrors UserSettings but
    allows finer-grained control per event type if needed in the future)."""

    id = UUID(primary_key=True)
    user = UUID(references=User, index=True)
    event_type = Varchar(length=100)  # e.g. "chat_complete", "billing", "system"
    in_app = Boolean(default=True)
    email = Boolean(default=False)
    slack = Boolean(default=False)
    teams = Boolean(default=False)
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())
