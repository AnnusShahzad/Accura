"""
Accura – Rate-Limiting Middleware
Per-user, tier-aware rate limiting of AI generation requests.

Backed by Redis when ``redis.url`` is configured (required for several
workers to share one budget); otherwise an in-process sliding window.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict

from sanic import Request
from sanic.response import json as sanic_json

from config import settings

logger = logging.getLogger("accura.rate_limiter")

# In-memory sliding window, used when Redis isn't configured
_buckets: dict[str, list[float]] = defaultdict(list)
_redis = None
_redis_failed = False

_WINDOWS = (("minute", 60), ("day", 86400))


_limit_cache: dict[str, tuple[float, tuple[int, int]]] = {}
_LIMIT_CACHE_SECONDS = 30


async def _get_limits(tier: str) -> tuple[int, int]:
    """Return (requests_per_minute, requests_per_day) for a tier.

    The subscription_plans table is authoritative (admins edit it from
    the dashboard); config.yaml only supplies defaults.
    """
    cached = _limit_cache.get(tier)
    if cached and time.monotonic() - cached[0] < _LIMIT_CACHE_SECONDS:
        return cached[1]

    rpm = int(settings.get(f"rate_limits.{tier}.requests_per_minute", 10))
    rpd = int(settings.get(f"rate_limits.{tier}.requests_per_day", 100))
    try:
        from models.subscription import SubscriptionPlan

        plan = await SubscriptionPlan.select(
            SubscriptionPlan.requests_per_minute, SubscriptionPlan.requests_per_day
        ).where(SubscriptionPlan.name == tier).first().run()
        if plan:
            rpm, rpd = int(plan["requests_per_minute"]), int(plan["requests_per_day"])
    except Exception as exc:
        logger.warning("Could not load plan limits for %s: %s", tier, exc)

    _limit_cache[tier] = (time.monotonic(), (rpm, rpd))
    return rpm, rpd


def _is_metered(request: Request) -> bool:
    """Only requests that start AI work count against the budget.

    Reading conversations is free: the chat page polls every few
    seconds while a response is generated and must never be throttled.
    """
    return request.method == "POST" and request.path.startswith("/api/v1/chat")


def _get_redis():
    global _redis, _redis_failed
    url = settings.get("redis.url", "")
    if not url or _redis_failed:
        return None
    if _redis is None:
        try:
            import redis.asyncio as aioredis

            _redis = aioredis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
        except Exception as exc:
            logger.warning("Redis unavailable, using in-memory rate limiting: %s", exc)
            _redis_failed = True
            return None
    return _redis


async def _counts_redis(client, user_id: str, now: float) -> dict[str, int]:
    counts: dict[str, int] = {}
    pipe = client.pipeline()
    for name, window in _WINDOWS:
        key = f"accura:rl:{user_id}:{name}"
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
    results = await pipe.execute()
    for i, (name, _) in enumerate(_WINDOWS):
        counts[name] = int(results[i * 2 + 1])
    return counts


async def _record_redis(client, user_id: str, now: float) -> None:
    pipe = client.pipeline()
    member = f"{now}:{uuid.uuid4().hex[:8]}"
    for name, window in _WINDOWS:
        key = f"accura:rl:{user_id}:{name}"
        pipe.zadd(key, {member: now})
        pipe.expire(key, window)
    await pipe.execute()


def _counts_memory(user_id: str, now: float) -> dict[str, int]:
    counts = {}
    for name, window in _WINDOWS:
        key = f"{user_id}:{name}"
        _buckets[key] = [ts for ts in _buckets[key] if now - ts < window]
        counts[name] = len(_buckets[key])
    return counts


def _record_memory(user_id: str, now: float) -> None:
    for name, _ in _WINDOWS:
        _buckets[f"{user_id}:{name}"].append(now)


async def rate_limit_middleware(request: Request):
    """Sanic middleware for rate-limiting API requests."""
    if not _is_metered(request):
        return

    user = getattr(request.ctx, "user", None)
    if not user:
        return

    user_id = str(user["id"])
    if user.get("is_guest"):
        # Guests spend the platform's AI keys; they get their own budget
        rpm_limit = int(settings.get("auth.guest.requests_per_minute", 5))
        rpd_limit = int(settings.get("auth.guest.requests_per_day", 30))
    else:
        rpm_limit, rpd_limit = await _get_limits(user.get("tier", "basic"))
    now = time.time()

    client = _get_redis()
    try:
        counts = await _counts_redis(client, user_id, now) if client else _counts_memory(user_id, now)
    except Exception as exc:
        logger.warning("Redis rate limit check failed, falling back to memory: %s", exc)
        client = None
        counts = _counts_memory(user_id, now)

    if counts["minute"] >= rpm_limit:
        logger.warning("Rate limit (RPM) exceeded for user %s", user_id)
        return sanic_json(
            {
                "success": False,
                "message": "Rate limit exceeded. Please wait a minute before sending more requests.",
                "retry_after_seconds": 60,
            },
            status=429,
            headers={"Retry-After": "60"},
        )

    if counts["day"] >= rpd_limit:
        logger.warning("Rate limit (RPD) exceeded for user %s", user_id)
        return sanic_json(
            {
                "success": False,
                "message": "Daily request limit exceeded. Upgrade your plan for higher limits.",
                "retry_after_seconds": 3600,
            },
            status=429,
            headers={"Retry-After": "3600"},
        )

    try:
        if client:
            await _record_redis(client, user_id, now)
        else:
            _record_memory(user_id, now)
    except Exception as exc:
        logger.warning("Could not record rate limit hit: %s", exc)
        _record_memory(user_id, now)
