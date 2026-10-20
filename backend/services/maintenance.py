"""
Accura – Maintenance jobs

Run periodically by the app (see app.py) and partly at startup:

  * purge guest accounts whose time is up, with everything they own
  * delete "temporary" conversations after a day
  * fail generation runs that a restart or crash left in "active", so
    users see Retry instead of an endless spinner -- free hosting tiers
    restart and sleep instances routinely
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from models.api_key import UserAPIKey
from models.chat import ChatAgent, ChatMessage, Conversation, Iteration
from models.mcp_server import MCPServer
from models.notification import Notification, NotificationPreference
from models.settings import UserSettings
from models.subscription import Subscription, Transaction
from models.user import User, UserProfile

logger = logging.getLogger("accura.maintenance")

TEMPORARY_CHAT_TTL = timedelta(hours=24)
# A run touches updated_at after every iteration; one this quiet is dead
STALE_RUN_AFTER = timedelta(minutes=40)


async def delete_conversations(conversation_ids: list) -> None:
    if not conversation_ids:
        return
    await ChatMessage.delete().where(ChatMessage.conversation.is_in(conversation_ids)).run()
    await Iteration.delete().where(Iteration.conversation.is_in(conversation_ids)).run()
    await ChatAgent.delete().where(ChatAgent.conversation.is_in(conversation_ids)).run()
    await Conversation.delete().where(Conversation.id.is_in(conversation_ids)).run()


async def delete_user_data(user_id) -> int:
    """Permanently delete a user and everything they own.

    Returns the number of conversations removed.
    """
    conv_ids = [
        c["id"] for c in await Conversation.select(Conversation.id).where(Conversation.user == user_id).run()
    ]
    await delete_conversations(conv_ids)
    await Transaction.delete().where(Transaction.user == user_id).run()
    await Subscription.delete().where(Subscription.user == user_id).run()
    for table in (UserAPIKey, Notification, NotificationPreference, UserSettings, UserProfile):
        await table.delete().where(table.user == user_id).run()
    await MCPServer.delete().where(MCPServer.user == user_id).run()
    await User.delete().where(User.id == user_id).run()
    return len(conv_ids)


async def purge_expired_guests(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    guests = await User.select(User.id).where(
        (User.is_guest == True) & (User.expires_at <= now)  # noqa: E712
    ).run()
    for guest in guests:
        await delete_user_data(guest["id"])
    if guests:
        logger.info("Purged %d expired guest account(s)", len(guests))
    return len(guests)


async def purge_temporary_conversations(now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(timezone.utc)) - TEMPORARY_CHAT_TTL
    rows = await Conversation.select(Conversation.id).where(
        (Conversation.is_temporary == True) & (Conversation.created_at <= cutoff)  # noqa: E712
    ).run()
    await delete_conversations([r["id"] for r in rows])
    return len(rows)


async def fail_interrupted_runs(*, all_active: bool = False, now: datetime | None = None) -> int:
    """Mark generation runs that can no longer finish as failed.

    With all_active (used at startup of a single-worker server) every
    active run is dead, since runs live in the process that started them.
    Otherwise only runs that stopped making progress are.
    """
    query = Conversation.select(Conversation.id).where(Conversation.status == "active")
    if not all_active:
        cutoff = (now or datetime.now(timezone.utc)) - STALE_RUN_AFTER
        query = query.where(Conversation.updated_at <= cutoff)
    rows = await query.run()

    reason = "The server restarted before this response finished. Press Retry to run it again."
    for row in rows:
        # Message first, status second: clients stop polling on the status
        await ChatMessage.insert(
            ChatMessage(
                id=str(uuid.uuid4()),
                conversation=row["id"],
                role="system",
                content=reason,
                metadata={"type": "error"},
            )
        ).run()
        await Conversation.update({
            Conversation.status: "failed",
            Conversation.metadata: {"error": reason},
            Conversation.updated_at: datetime.now(timezone.utc),
        }).where(Conversation.id == row["id"]).run()
    if rows:
        logger.warning("Marked %d interrupted run(s) as failed", len(rows))
    return len(rows)


async def run_periodic_maintenance() -> None:
    from services.billing_service import renew_due_subscriptions

    for job in (purge_expired_guests, purge_temporary_conversations, fail_interrupted_runs,
                renew_due_subscriptions):
        try:
            await job()
        except Exception:
            logger.exception("Maintenance job %s failed", job.__name__)
