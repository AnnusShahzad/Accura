"""
Accura – MCP Server Model
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

from models.user import User


class MCPServer(Table, tablename="mcp_servers"):
    """User-level or global MCP server configuration."""

    id = UUID(primary_key=True)
    user = UUID(references=User, null=True, default=None, index=True)  # NULL = global
    name = Varchar(length=255)
    url = Text()
    api_key_encrypted = Text(default="")
    description = Text(default="")
    is_active = Boolean(default=True)
    is_global = Boolean(default=False)
    transport = Varchar(length=20, default="sse")  # sse | stdio | http
    headers = JSONB(default={})
    metadata = JSONB(default={})
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow(), auto_update=TimestamptzNow())
