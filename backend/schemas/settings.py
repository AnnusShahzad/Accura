"""
Accura – Settings Schemas
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UpdateSettingsRequest(BaseModel):
    global_threshold: Optional[float] = Field(None, ge=0, le=100)
    max_iterations: Optional[int] = Field(None, ge=1, le=50)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=600)
    hide_evaluator_scoring: Optional[bool] = None
    preferred_generator_model: Optional[str] = None
    preferred_evaluator_model: Optional[str] = None
    preferred_critic_model: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    notify_in_app: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_slack: Optional[bool] = None
    notify_teams: Optional[bool] = None
    slack_webhook_url: Optional[str] = Field(None, max_length=500)
    teams_webhook_url: Optional[str] = Field(None, max_length=500)
    dark_mode: Optional[bool] = None
    search_enabled: Optional[bool] = None


class SettingsResponse(BaseModel):
    id: str
    user_id: str
    global_threshold: float
    max_iterations: int
    timeout_seconds: int
    hide_evaluator_scoring: bool
    preferred_generator_model: str
    preferred_evaluator_model: str
    preferred_critic_model: str
    notifications_enabled: bool
    notify_in_app: bool
    notify_email: bool
    notify_slack: bool
    notify_teams: bool
    slack_webhook_url: str
    teams_webhook_url: str
    dark_mode: bool
    search_enabled: bool
