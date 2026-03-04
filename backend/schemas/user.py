"""
Accura – User & Profile Schemas
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    tier: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: str


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=150)
    last_name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=30)
    company: Optional[str] = Field(None, max_length=255)
    timezone: Optional[str] = Field(None, max_length=64)
    avatar_url: Optional[str] = None


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    first_name: str
    last_name: str
    avatar_url: str
    phone: str
    company: str
    timezone: str
