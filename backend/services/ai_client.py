"""
Accura – AI Client Factory
Provides a unified interface to call OpenAI-compatible providers.
Handles BYOK (user keys) vs platform keys.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx
from openai import AsyncOpenAI

from config import settings
from models.api_key import UserAPIKey
from utils.crypto import decrypt

logger = logging.getLogger("accura.ai_client")

# Provider → base URL mapping (defaults)
_PROVIDER_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


async def _resolve_api_key(user_id: str | None, provider: str) -> tuple[str, str]:
    """Return (api_key, base_url) – user BYOK first, then platform key."""

    # 1) Try user's own key
    if user_id:
        user_key = await UserAPIKey.select().where(
            (UserAPIKey.user == user_id)
            & (UserAPIKey.provider == provider)
            & (UserAPIKey.is_active == True)
        ).first().run()

        if user_key:
            key = decrypt(user_key["key_encrypted"])
            base_url = user_key["base_url"] or _PROVIDER_URLS.get(provider, "")
            return key, base_url

    # 2) Fall back to platform key from config
    platform_key = settings.get(f"ai.providers.{provider}.api_key", "")
    base_url = settings.get(f"ai.providers.{provider}.base_url", _PROVIDER_URLS.get(provider, ""))

    if not platform_key:
        raise RuntimeError(f"No API key available for provider '{provider}'")

    return platform_key, base_url


async def get_client(user_id: str | None, provider: str) -> AsyncOpenAI:
    """Return an AsyncOpenAI client configured for the given provider + user."""
    api_key, base_url = await _resolve_api_key(user_id, provider)
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def chat_completion(
    user_id: str | None,
    provider: str,
    model: str,
    messages: list[dict],
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 120,
) -> dict:
    """Single chat completion call. Returns {"content": str, "usage": dict}."""

    client = await get_client(user_id, provider)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    except Exception as exc:
        logger.exception("AI completion failed: provider=%s model=%s", provider, model)
        raise

    choice = response.choices[0]
    usage = response.usage

    return {
        "content": choice.message.content or "",
        "usage": {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        },
        "finish_reason": choice.finish_reason,
    }
