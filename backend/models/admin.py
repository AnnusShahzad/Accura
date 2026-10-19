"""
Accura – Admin Configuration Models
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


class AdminConfig(JSONTable, tablename="admin_config"):
    """Key-value admin configuration store.
    Used for dynamic runtime settings that override YAML defaults.
    """

    id = UUID(primary_key=True)
    key = Varchar(length=255, unique=True, index=True)
    value = JSONB(default={})
    description = Text(default="")
    updated_by = Varchar(length=320, default="system")
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())


class SystemPrompt(Table, tablename="system_prompts"):
    """Admin-editable system prompts for Generator, Evaluator, Reprompt AI."""

    id = UUID(primary_key=True)
    role = Varchar(length=30, unique=True)  # generator | evaluator | reprompt
    prompt = Text()
    is_active = Boolean(default=True)
    version = Varchar(length=20, default="1.0")
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())


class DomainRule(Table, tablename="domain_rules"):
    """Whitelist / blacklist domains for search."""

    id = UUID(primary_key=True)
    domain = Varchar(length=500, index=True)
    rule_type = Varchar(length=10)  # whitelist | blacklist
    created_at = Timestamptz(default=TimestamptzNow())
