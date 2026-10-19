"""
Accura – API Key Schemas (BYOK)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


_URL_PATTERN = r"^(https?://\S+)?$"


class CreateAPIKeyRequest(BaseModel):
    provider: str = Field(pattern="^(openai|deepseek|anthropic|google|custom)$")
    label: str = Field(default="", max_length=255)
    api_key: str = Field(min_length=1, max_length=1000)
    base_url: str = Field(default="", max_length=500, pattern=_URL_PATTERN)

    @model_validator(mode="after")
    def custom_needs_url(self):
        if self.provider == "custom" and not self.base_url:
            raise ValueError("A base URL is required for custom providers")
        self.api_key = self.api_key.strip()
        return self


class UpdateAPIKeyRequest(BaseModel):
    label: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, min_length=1, max_length=1000)
    base_url: Optional[str] = Field(None, max_length=500, pattern=_URL_PATTERN)
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    id: str
    provider: str
    label: str
    base_url: str
    is_active: bool
    # NOTE: never expose the raw key
    key_preview: str  # e.g. "sk-...abc"
    created_at: str
