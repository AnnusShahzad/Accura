"""
Accura – Rate-Limiting Middleware
Per-user, tier-aware rate limiting backed by an in-memory store
(swap to Redis for multi-worker deployments).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from sanic import Request
from sanic.response import json as sanic_json

from config import settings

logger = logging.getLogger("accura.rate_limiter")

# In-memory sliding window – replace with Redis in production
_buckets: dict[str, list[float]] = defaultdict(list)


def _get_limits(tier: str) -> tuple[int, int]:
    """Return (requests_per_minute, requests_per_day) for a tier."""
    rpm = settings.get(f"rate_limits.{tier}.requests_per_minute", 10)
    rpd = settings.get(f"rate_limits.{tier}.requests_per_day", 100)
    return int(rpm), int(rpd)


def _clean_bucket(bucket: list[float], window: float) -> list[float]:
    now = time.time()
    return [ts for ts in bucket if now - ts < window]


async def rate_limit_middleware(request: Request):
    """Sanic middleware for rate-limiting API requests."""
    # Only rate-limit authenticated AI / chat endpoints
    if not request.path.startswith("/api/v1/chat"):
        return

    user = getattr(request.ctx, "user", None)
    if not user:
        return

    user_id = str(user["id"])
    tier = user.get("tier", "basic")
    rpm_limit, rpd_limit = _get_limits(tier)

    now = time.time()

    # Per-minute bucket
    minute_key = f"{user_id}:minute"
    _buckets[minute_key] = _clean_bucket(_buckets[minute_key], 60)
    if len(_buckets[minute_key]) >= rpm_limit:
        logger.warning("Rate limit (RPM) exceeded for user %s", user_id)
        return sanic_json(
            {
                "success": False,
                "message": "Rate limit exceeded. Please wait before sending more requests.",
                "retry_after_seconds": 60,
            },
            status=429,
        )

    # Per-day bucket
    day_key = f"{user_id}:day"
    _buckets[day_key] = _clean_bucket(_buckets[day_key], 86400)
    if len(_buckets[day_key]) >= rpd_limit:
        logger.warning("Rate limit (RPD) exceeded for user %s", user_id)
        return sanic_json(
            {
                "success": False,
                "message": "Daily request limit exceeded. Upgrade your plan for higher limits.",
                "retry_after_seconds": 3600,
            },
            status=429,
        )

    _buckets[minute_key].append(now)
    _buckets[day_key].append(now)
