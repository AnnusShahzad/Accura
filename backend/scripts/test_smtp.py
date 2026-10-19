"""
Send a test email with the configured SMTP settings.

    python scripts/test_smtp.py you@example.com
"""

import argparse
import asyncio

import _bootstrap  # noqa: F401

from config import settings
from utils.email import send_email


async def main(to: str) -> None:
    for key in ("host", "port", "user", "from_email", "use_tls"):
        print(f"smtp.{key:<10} = {settings.get(f'smtp.{key}')}")
    try:
        await send_email(
            to=to,
            subject="Test from Accura",
            text_body="This is a test email to verify the SMTP configuration.",
        )
    except Exception as exc:
        raise SystemExit(f"Failed: {type(exc).__name__}: {exc}")
    print(f"Sent a test email to {to}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("to")
    asyncio.run(main(parser.parse_args().to))
