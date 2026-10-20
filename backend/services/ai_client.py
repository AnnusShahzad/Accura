"""
Accura – AI Client Factory
Provides a unified interface to call OpenAI-compatible providers.
Handles BYOK (user keys) vs platform keys.
"""

from __future__ import annotations

import logging

import openai
from openai import AsyncOpenAI

from config import settings
from models.api_key import UserAPIKey
from utils.crypto import decrypt
from utils.exceptions import AIProviderError

logger = logging.getLogger("accura.ai_client")

# Provider → base URL mapping (defaults). Every entry speaks the OpenAI
# chat-completions protocol; Anthropic and Google expose compatible
# endpoints for exactly this purpose.
_PROVIDER_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "anthropic": "https://api.anthropic.com/v1/",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

# OpenAI reasoning models reject `max_tokens` and any non-default
# temperature; they want `max_completion_tokens` instead.
_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _is_reasoning_model(model: str) -> bool:
    name = model.split("/")[-1].lower()
    return name.startswith(_REASONING_PREFIXES)


async def _resolve_api_key(user_id: str | None, provider: str) -> tuple[str, str]:
    """Return (api_key, base_url) – user BYOK first, then platform key."""

    default_url = settings.get(f"ai.providers.{provider}.base_url") or _PROVIDER_URLS.get(provider, "")

    # 1) Try user's own key
    if user_id:
        user_key = await UserAPIKey.select().where(
            (UserAPIKey.user == user_id)
            & (UserAPIKey.provider == provider)
            & (UserAPIKey.is_active == True)  # noqa: E712
        ).order_by(UserAPIKey.created_at, ascending=False).first().run()

        if user_key:
            try:
                key = decrypt(user_key["key_encrypted"])
            except Exception:
                raise AIProviderError(
                    f"Your saved {provider} API key could not be decrypted. Please re-add it."
                )
            return key, user_key["base_url"] or default_url

    # 2) Fall back to platform key from config
    platform_key = settings.get(f"ai.providers.{provider}.api_key", "")
    if not platform_key:
        raise AIProviderError(
            f"No API key configured for provider '{provider}'. "
            "Add your own key under Settings → API Keys."
        )
    if not default_url:
        raise AIProviderError(f"No base URL configured for provider '{provider}'.")

    return platform_key, default_url


async def get_client(user_id: str | None, provider: str, timeout: int = 120) -> AsyncOpenAI:
    """Return an AsyncOpenAI client configured for the given provider + user."""
    api_key, base_url = await _resolve_api_key(user_id, provider)
    return AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=1)


def _describe_error(exc: Exception, provider: str, model: str) -> str:
    if isinstance(exc, openai.AuthenticationError):
        return f"{provider} rejected the API key (401). Check the key under Settings → API Keys."
    if isinstance(exc, openai.PermissionDeniedError):
        return f"{provider} denied access to model '{model}'."
    if isinstance(exc, openai.NotFoundError):
        return f"Model '{model}' was not found on {provider}."
    if isinstance(exc, openai.RateLimitError):
        return f"{provider} rate limit or quota exceeded."
    if isinstance(exc, openai.APITimeoutError):
        return f"{provider} timed out."
    if isinstance(exc, openai.APIConnectionError):
        return f"Could not connect to {provider}."
    if isinstance(exc, openai.APIStatusError):
        detail = getattr(exc, "message", "") or str(exc)
        return f"{provider} returned {exc.status_code}: {detail[:300]}"
    return f"{provider} request failed: {exc}"


async def chat_completion(
    user_id: str | None,
    provider: str,
    model: str,
    messages: list[dict],
    *,
    temperature: float | None = 0.7,
    max_tokens: int = 4096,
    timeout: int = 120,
    tools: list[dict] | None = None,
) -> dict:
    """Single chat completion call.

    Returns {"content": str, "usage": dict, "finish_reason": str,
             "tool_calls": list[dict]}.
    """

    client = await get_client(user_id, provider, timeout=timeout)

    params: dict = {"model": model, "messages": messages}
    if tools:
        params["tools"] = tools
    if provider == "openai" and _is_reasoning_model(model):
        params["max_completion_tokens"] = max_tokens
    else:
        params["max_tokens"] = max_tokens
        if temperature is not None:
            params["temperature"] = temperature

    try:
        async with client:
            # Providers disagree on parameter names; adapt once on the
            # specific "unsupported parameter" errors and retry.
            for _ in range(3):
                try:
                    response = await client.chat.completions.create(**params)
                    break
                except openai.BadRequestError as exc:
                    msg = str(exc).lower()
                    if "max_tokens" in msg and "max_completion_tokens" in msg and "max_tokens" in params:
                        params["max_completion_tokens"] = params.pop("max_tokens")
                    elif "temperature" in msg and "temperature" in params:
                        params.pop("temperature")
                    else:
                        raise
            else:
                raise AIProviderError(f"{provider} rejected the request parameters for '{model}'.")
    except AIProviderError:
        raise
    except Exception as exc:
        logger.warning("AI completion failed: provider=%s model=%s: %s", provider, model, exc)
        raise AIProviderError(_describe_error(exc, provider, model)) from exc

    if not response.choices:
        raise AIProviderError(f"{provider} returned no choices for '{model}'.")

    choice = response.choices[0]
    usage = response.usage
    tool_calls = [
        {
            "id": tc.id,
            "name": tc.function.name,
            "arguments": tc.function.arguments or "{}",
        }
        for tc in (choice.message.tool_calls or [])
        if getattr(tc, "function", None)
    ]

    return {
        "content": choice.message.content or "",
        "usage": {
            "prompt_tokens": (usage.prompt_tokens or 0) if usage else 0,
            "completion_tokens": (usage.completion_tokens or 0) if usage else 0,
            "total_tokens": (usage.total_tokens or 0) if usage else 0,
        },
        "finish_reason": choice.finish_reason,
        "tool_calls": tool_calls,
    }
