"""
Accura – User API Key Model (BYOK)
"""

from piccolo.columns import (
    UUID,
    Boolean,
    Text,
    Timestamptz,
    Varchar,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from models.user import User


class UserAPIKey(Table, tablename="user_api_keys"):
    """Encrypted API keys provided by users (BYOK – Bring Your Own Keys).
    The `key_encrypted` field is encrypted at rest using Fernet.
    """

    id = UUID(primary_key=True)
    user = UUID(references=User, index=True)
    provider = Varchar(length=50)  # openai | deepseek | anthropic | custom
    label = Varchar(length=255, default="")
    key_encrypted = Text()  # Fernet-encrypted
    base_url = Text(default="")  # For OpenAI-compatible endpoints
    is_active = Boolean(default=True)
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())
