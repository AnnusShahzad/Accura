"""
Accura – Contact Request Model
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


class ContactRequest(Table, tablename="contact_requests"):
    """Contact form submissions (e.g. business account enquiries)."""

    id = UUID(primary_key=True)
    name = Varchar(length=255)
    email = Varchar(length=320)
    company = Varchar(length=255, default="")
    subject = Varchar(length=500, default="")
    message = Text()
    request_type = Varchar(length=30, default="general")  # general | business_upgrade | support
    is_resolved = Boolean(default=False)
    resolved_by = Varchar(length=320, default="")
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow(), auto_update=TimestamptzNow())
