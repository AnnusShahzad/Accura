"""
Permanently delete a user and everything they own (GDPR erasure).

    python scripts/delete_user.py user@example.com [--yes]

Goes through the ORM, so it works with both the SQLite and Postgres
engines and doesn't need the server to be stopped.
"""

import argparse
import asyncio

import _bootstrap  # noqa: F401

from models.user import User
from services.maintenance import delete_user_data


async def main(email: str, assume_yes: bool) -> None:
    user = await User.select(User.id, User.username).where(User.email == email).first().run()
    if not user:
        raise SystemExit(f"No user found with email {email}")
    user_id = user["id"]

    if not assume_yes:
        answer = input(f"Delete {user['username']} <{email}> and all their data? [y/N] ")
        if answer.strip().lower() != "y":
            raise SystemExit("Aborted.")

    deleted = await delete_user_data(user_id)

    print(f"Deleted {user['username']} <{email}> and {deleted} conversation(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.yes))
