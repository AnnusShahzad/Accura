"""
Accura – API Key Schemas (BYOK)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateAPIKeyRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    label: str = Field(default="", max_length=255)
    api_key: str = Field(min_length=1)
    base_url: str = ""


class UpdateAPIKeyRequest(BaseModel):
    label: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = None
    base_url: Optional[str] = None
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
