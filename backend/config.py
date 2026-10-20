"""
Accura Backend – Configuration Loader
Loads settings from config.yaml, then overrides with environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = os.getenv("ACCURA_CONFIG_PATH", str(_BASE_DIR / "config.yaml"))
_ENV_PATH = _BASE_DIR / ".env"

# Real environment variables win over .env so that docker-compose
# `environment:` entries and test fixtures can override the file.
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH, override=False)
else:
    load_dotenv(override=False)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _bool(v: str) -> bool:
    return v.strip().lower() in ("true", "1", "yes", "on")


def _env_overrides() -> dict:
    """Map environment variables to nested config keys.

    Later entries win when two variables target the same key, so the
    platform conventions (PORT, DATABASE_URL) come first and the explicit
    Accura variables can still override them.
    """
    mapping: list[tuple[str, str, type]] = [
        # Platform conventions (Render, Railway, Fly, Heroku-style hosts)
        ("PORT", "app.port", int),
        ("DATABASE_URL", "database.url", str),
        ("APP_ENV", "app.environment", str),
        ("APP_HOST", "app.host", str),
        ("APP_PORT", "app.port", int),
        ("APP_DEBUG", "app.debug", _bool),
        ("APP_WORKERS", "app.workers", int),
        ("APP_SECRET_KEY", "app.secret_key", str),
        ("APP_FRONTEND_URL", "app.frontend_url", str),
        ("APP_CORS_ORIGINS", "app.cors_origins", str),
        ("DB_ENGINE", "database.engine", str),
        ("DB_SQLITE_PATH", "database.sqlite_path", str),
        ("DB_HOST", "database.host", str),
        ("DB_PORT", "database.port", int),
        ("DB_NAME", "database.name", str),
        ("DB_USER", "database.user", str),
        ("DB_PASSWORD", "database.password", str),
        ("DB_POOL_SIZE", "database.pool_size", int),
        ("REDIS_URL", "redis.url", str),
        ("JWT_SECRET", "jwt.secret", str),
        ("JWT_ALGORITHM", "jwt.algorithm", str),
        ("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "jwt.access_token_expire_minutes", int),
        ("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "jwt.refresh_token_expire_days", int),
        ("SMTP_HOST", "smtp.host", str),
        ("SMTP_PORT", "smtp.port", int),
        ("SMTP_USER", "smtp.user", str),
        ("SMTP_PASSWORD", "smtp.password", str),
        ("SMTP_FROM_NAME", "smtp.from_name", str),
        ("SMTP_FROM_EMAIL", "smtp.from_email", str),
        ("SMTP_USE_TLS", "smtp.use_tls", _bool),
        ("OPENAI_API_KEY", "ai.providers.openai.api_key", str),
        ("OPENAI_BASE_URL", "ai.providers.openai.base_url", str),
        ("DEEPSEEK_API_KEY", "ai.providers.deepseek.api_key", str),
        ("DEEPSEEK_BASE_URL", "ai.providers.deepseek.base_url", str),
        ("ANTHROPIC_API_KEY", "ai.providers.anthropic.api_key", str),
        ("GOOGLE_AI_API_KEY", "ai.providers.google.api_key", str),
        ("CUSTOM_AI_API_KEY", "ai.providers.custom.api_key", str),
        ("CUSTOM_AI_BASE_URL", "ai.providers.custom.base_url", str),
        ("DEFAULT_AI_PROVIDER", "ai.default_provider", str),
        ("DEFAULT_GENERATOR_MODEL", "ai.default_generator_model", str),
        ("DEFAULT_EVALUATOR_MODEL", "ai.default_evaluator_model", str),
        ("DEFAULT_REPROMPT_MODEL", "ai.default_reprompt_model", str),
        ("ENCRYPTION_KEY", "security.encryption_key", str),
        ("GOOGLE_API_KEY", "search.google_api_key", str),
        ("GOOGLE_CSE_ID", "search.google_cse_id", str),
        ("STRIPE_SECRET_KEY", "billing.stripe_secret_key", str),
        ("STRIPE_WEBHOOK_SECRET", "billing.stripe_webhook_secret", str),
        ("STRIPE_PRICE_PRO_MONTHLY", "billing.stripe_price_ids.pro_monthly", str),
        ("STRIPE_PRICE_PRO_YEARLY", "billing.stripe_price_ids.pro_yearly", str),
        ("SUPPORT_EMAIL", "branding.support_email", str),
        ("REGISTRATION_ENABLED", "auth.registration_enabled", _bool),
        ("GUEST_ENABLED", "auth.guest.enabled", _bool),
        ("GUEST_TTL_HOURS", "auth.guest.ttl_hours", int),
        ("GUEST_REQUESTS_PER_MINUTE", "auth.guest.requests_per_minute", int),
        ("GUEST_REQUESTS_PER_DAY", "auth.guest.requests_per_day", int),
        ("GUEST_MAX_ITERATIONS", "auth.guest.max_iterations", int),
        ("GUEST_SIGNUPS_PER_HOUR", "auth.guest.signups_per_hour", int),
        ("ADMIN_EMAIL", "auth.bootstrap_admin.email", str),
        ("ADMIN_PASSWORD", "auth.bootstrap_admin.password", str),
        ("ADMIN_USERNAME", "auth.bootstrap_admin.username", str),
        ("ALLOW_PRIVATE_URLS", "security.allow_private_urls", _bool),
        ("COMPANY_NAME", "branding.company_name", str),
        ("COMPANY_LOGO_URL", "branding.logo_url", str),
    ]
    overrides: dict[str, Any] = {}
    for env_key, config_path, cast in mapping:
        value = os.getenv(env_key)
        # Treat "FOO=" in a .env file as unset rather than crashing on int("")
        if value is not None and value != "":
            parts = config_path.split(".")
            ref = overrides
            for part in parts[:-1]:
                ref = ref.setdefault(part, {})
            ref[parts[-1]] = cast(value)
    return overrides


class _Settings:
    """Singleton settings container with attribute access.

    Values are layered: config.yaml < environment variables < runtime
    overrides (admin_config table, applied via ``apply_overrides``).
    """

    _instance: _Settings | None = None
    _base: dict[str, Any] = {}
    _overrides: dict[str, Any] = {}
    _data: dict[str, Any] = {}

    def __new__(cls) -> _Settings:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        self._base = _deep_merge(_load_yaml(_CONFIG_PATH), _env_overrides())
        self._data = _deep_merge(self._base, self._overrides)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Retrieve a nested value via dot-separated key."""
        parts = dotted_key.split(".")
        ref: Any = self._data
        for part in parts:
            if isinstance(ref, dict):
                ref = ref.get(part)
            else:
                return default
            if ref is None:
                return default
        return ref

    def as_dict(self) -> dict:
        return self._data.copy()

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        """Replace the runtime override layer with ``{"dotted.key": value}``."""
        nested: dict[str, Any] = {}
        for dotted_key, value in overrides.items():
            parts = dotted_key.split(".")
            ref = nested
            for part in parts[:-1]:
                ref = ref.setdefault(part, {})
            ref[parts[-1]] = value
        self._overrides = nested
        self._data = _deep_merge(self._base, nested)

    def reload(self) -> None:
        """Hot-reload configuration (useful for admin changes)."""
        self._load()


settings = _Settings()
