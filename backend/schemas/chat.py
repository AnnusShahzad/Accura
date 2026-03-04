"""
Accura – Chat / Conversation Schemas
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Conversation", max_length=500)
    prompt: str = Field(min_length=1)
    generator_model: str = Field(default="gpt-5.2")
    generator_provider: str = Field(default="openai")
    evaluator_model: Optional[str] = None
    evaluator_provider: Optional[str] = None
    search_enabled: bool = False
    is_temporary: bool = False
    threshold: Optional[float] = Field(None, ge=0, le=100)
    max_iterations: Optional[int] = Field(None, ge=1, le=50)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=600)


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)


class AddAgentRequest(BaseModel):
    """Add a new AI agent mid-conversation."""
    provider: str
    model: str
    role: str = Field(default="generator")


class ConversationResponse(BaseModel):
    id: str
    title: str
    prompt: str
    status: str
    best_response: str
    best_score: float
    tokens_input: int
    tokens_output: int
    search_enabled: bool
    is_temporary: bool
    created_at: str
    agents: list[dict] = []
    iterations: list[dict] = []


class ConversationListResponse(BaseModel):
    id: str
    title: str
    status: str
    best_score: float
    created_at: str


class IterationResponse(BaseModel):
    id: str
    iteration_number: int
    agent_id: str
    rephrased_prompt: str
    response: str
    score: float
    evaluation_reasoning: str
    tokens_input: int
    tokens_output: int
    timed_out: bool
    duration_ms: int
    created_at: str
