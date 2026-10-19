"""
Permanently delete a user and everything they own (GDPR erasure).

    python scripts/delete_user.py user@example.com [--yes]

Goes through the ORM, so it works with both the SQLite and Postgres
engines and doesn't need the server to be stopped.
"""

import argparse
import asyncio

import _bootstrap  # noqa: F401

from models.api_key import UserAPIKey
from models.chat import ChatAgent, ChatMessage, Conversation, Iteration
from models.mcp_server import MCPServer
from models.notification import Notification, NotificationPreference
from models.settings import UserSettings
from models.subscription import Subscription, Transaction
from models.user import User, UserProfile


async def main(email: str, assume_yes: bool) -> None:
    user = await User.select(User.id, User.username).where(User.email == email).first().run()
    if not user:
        raise SystemExit(f"No user found with email {email}")
    user_id = user["id"]

    if not assume_yes:
        answer = input(f"Delete {user['username']} <{email}> and all their data? [y/N] ")
        if answer.strip().lower() != "y":
            raise SystemExit("Aborted.")

    conv_ids = [c["id"] for c in await Conversation.select(Conversation.id).where(Conversation.user == user_id).run()]
    if conv_ids:
        await ChatMessage.delete().where(ChatMessage.conversation.is_in(conv_ids)).run()
        await Iteration.delete().where(Iteration.conversation.is_in(conv_ids)).run()
        await ChatAgent.delete().where(ChatAgent.conversation.is_in(conv_ids)).run()
        await Conversation.delete().where(Conversation.id.is_in(conv_ids)).run()

    await Transaction.delete().where(Transaction.user == user_id).run()
    await Subscription.delete().where(Subscription.user == user_id).run()
    for table in (UserAPIKey, Notification, NotificationPreference, UserSettings, UserProfile):
        await table.delete().where(table.user == user_id).run()
    await MCPServer.delete().where(MCPServer.user == user_id).run()
    await User.delete().where(User.id == user_id).run()

    print(f"Deleted {user['username']} <{email}> and {len(conv_ids)} conversation(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.yes))
