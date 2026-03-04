"""
Accura – MCP Server Schemas
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateMCPServerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    api_key: Optional[str] = None
    description: str = ""
    transport: str = Field(default="sse", pattern="^(sse|stdio|http)$")
    headers: dict = {}
    metadata: dict = {}


class UpdateMCPServerRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = None
    api_key: Optional[str] = None
    description: Optional[str] = None
    transport: Optional[str] = Field(None, pattern="^(sse|stdio|http)$")
    headers: Optional[dict] = None
    metadata: Optional[dict] = None
    is_active: Optional[bool] = None


class MCPServerResponse(BaseModel):
    id: str
    name: str
    url: str
    description: str
    is_active: bool
    is_global: bool
    transport: str
    headers: dict
    metadata: dict
    created_at: str
