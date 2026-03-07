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

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = os.getenv("ACCURA_CONFIG_PATH", str(_BASE_DIR / "config.yaml"))


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


def _env_overrides() -> dict:
    """Map environment variables to nested config keys."""
    mapping: list[tuple[str, str, type]] = [
        ("APP_ENV", "app.environment", str),
        ("APP_HOST", "app.host", str),
        ("APP_PORT", "app.port", int),
        ("APP_DEBUG", "app.debug", lambda v: v.lower() in ("true", "1", "yes")),
        ("APP_WORKERS", "app.workers", int),
        ("APP_SECRET_KEY", "app.secret_key", str),
        ("APP_FRONTEND_URL", "app.frontend_url", str),
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
        ("SMTP_USE_TLS", "smtp.use_tls", lambda v: v.lower() in ("true", "1", "yes")),
        ("OPENAI_API_KEY", "ai.providers.openai.api_key", str),
        ("DEEPSEEK_API_KEY", "ai.providers.deepseek.api_key", str),
        ("ENCRYPTION_KEY", "security.encryption_key", str),
        ("GOOGLE_API_KEY", "search.google_api_key", str),
        ("GOOGLE_CSE_ID", "search.google_cse_id", str),
        ("STRIPE_SECRET_KEY", "billing.stripe_secret_key", str),
        ("STRIPE_WEBHOOK_SECRET", "billing.stripe_webhook_secret", str),
        ("COMPANY_NAME", "branding.company_name", str),
        ("COMPANY_LOGO_URL", "branding.logo_url", str),
    ]
    overrides: dict[str, Any] = {}
    for env_key, config_path, cast in mapping:
        value = os.getenv(env_key)
        if value is not None:
            parts = config_path.split(".")
            ref = overrides
            for part in parts[:-1]:
                ref = ref.setdefault(part, {})
            ref[parts[-1]] = cast(value)
    return overrides


class _Settings:
    """Singleton settings container with attribute access."""

    _instance: _Settings | None = None
    _data: dict[str, Any] = {}

    def __new__(cls) -> _Settings:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            base = _load_yaml(_CONFIG_PATH)
            cls._instance._data = _deep_merge(base, _env_overrides())
        return cls._instance

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

    def reload(self) -> None:
        """Hot-reload configuration (useful for admin changes)."""
        base = _load_yaml(_CONFIG_PATH)
        self._data = _deep_merge(base, _env_overrides())


settings = _Settings()
