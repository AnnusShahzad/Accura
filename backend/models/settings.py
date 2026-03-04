"""
Accura – User Settings Model
"""

from piccolo.columns import (
    UUID,
    Boolean,
    Integer,
    Numeric,
    Varchar,
    JSONB,
    Timestamptz,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from models.user import User


class UserSettings(Table, tablename="user_settings"):
    """Per-user settings (one row per user)."""

    id = UUID(primary_key=True)
    user = UUID(references=User, unique=True, index=True)

    # Evaluation
    global_threshold = Numeric(digits=(5, 2), default=75.00)
    max_iterations = Integer(default=5)
    timeout_seconds = Integer(default=120)
    hide_evaluator_scoring = Boolean(default=False)

    # Preferred models
    preferred_generator_model = Varchar(length=100, default="gpt-5.2")
    preferred_evaluator_model = Varchar(length=100, default="gpt-5.1")
    preferred_critic_model = Varchar(length=100, default="gpt-5.1")

    # Notifications
    notifications_enabled = Boolean(default=True)
    notify_in_app = Boolean(default=True)
    notify_email = Boolean(default=False)
    notify_slack = Boolean(default=False)
    notify_teams = Boolean(default=False)
    slack_webhook_url = Varchar(length=500, default="")
    teams_webhook_url = Varchar(length=500, default="")

    # Appearance
    dark_mode = Boolean(default=False)

    # Search
    search_enabled = Boolean(default=False)

    # Extra / overflow
    extra = JSONB(default={})

    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow(), auto_update=TimestamptzNow())
