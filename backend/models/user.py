"""
Accura – User & Profile Models
"""

from piccolo.columns import (
    UUID,
    Boolean,
    Serial,
    Text,
    Timestamptz,
    Varchar,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table


class User(Table, tablename="users"):
    """Core user account."""

    id = UUID(primary_key=True)
    email = Varchar(length=320, unique=True, index=True)
    username = Varchar(length=150, unique=True, index=True)
    hashed_password = Text()
    is_active = Boolean(default=True)
    is_verified = Boolean(default=False)
    is_admin = Boolean(default=False)
    tier = Varchar(length=20, default="basic")  # basic | pro | business
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())


class UserProfile(Table, tablename="user_profiles"):
    """Extended user profile / personal info."""

    id = UUID(primary_key=True)
    user = UUID(references=User, unique=True)
    first_name = Varchar(length=150, default="")
    last_name = Varchar(length=150, default="")
    avatar_url = Text(default="")
    phone = Varchar(length=30, default="")
    company = Varchar(length=255, default="")
    timezone = Varchar(length=64, default="UTC")
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())
