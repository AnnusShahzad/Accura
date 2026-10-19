"""
Create an admin account, or promote an existing user to admin.

    python scripts/create_admin.py admin@example.com
    python scripts/create_admin.py admin@example.com --username admin --password 'S3cure!Pass'

Without --password an existing user is promoted; a new account needs one.
Accounts created here are marked verified.
"""

import argparse
import asyncio
import getpass
import uuid

import _bootstrap  # noqa: F401

from models.settings import UserSettings
from models.user import User, UserProfile
from services.auth_service import hash_password, validate_password
from utils.db_schema import ensure_schema
from utils.exceptions import ValidationError


async def main(email: str, username: str | None, password: str | None) -> None:
    await ensure_schema()
    user = await User.select().where(User.email == email).first().run()
    if user:
        await User.update({User.is_admin: True, User.is_verified: True}).where(User.id == user["id"]).run()
        print(f"Promoted {email} to admin.")
        return

    if not password:
        password = getpass.getpass("Password for the new admin: ")
    try:
        validate_password(password)
    except ValidationError as exc:
        raise SystemExit(f"Weak password: {exc.message}")

    user_id = str(uuid.uuid4())
    await User.insert(User(
        id=user_id,
        email=email,
        username=username or email.split("@")[0].replace(".", "_")[:150],
        hashed_password=hash_password(password),
        is_admin=True,
        is_verified=True,
    )).run()
    await UserProfile.insert(UserProfile(id=str(uuid.uuid4()), user=user_id)).run()
    await UserSettings.insert(UserSettings(id=str(uuid.uuid4()), user=user_id)).run()
    print(f"Created admin {email}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("--username")
    parser.add_argument("--password")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.username, args.password))
