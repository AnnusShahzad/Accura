"""
Accura – Webhook Utilities (Slack / Teams)
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("accura.webhooks")


async def send_slack_notification(webhook_url: str, text: str, *, blocks: list | None = None) -> bool:
    """Post a message to a Slack incoming webhook."""
    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("Failed to send Slack notification")
        return False


async def send_teams_notification(webhook_url: str, title: str, text: str) -> bool:
    """Post a message to a Microsoft Teams incoming webhook."""
    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": title,
        "themeColor": "0076D7",
        "title": title,
        "sections": [{"activityTitle": title, "text": text}],
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("Failed to send Teams notification")
        return False
