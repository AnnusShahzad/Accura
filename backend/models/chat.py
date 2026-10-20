"""
Accura – Chat, Conversation, Agent & Iteration Models
"""

import decimal

from piccolo.columns import (
    UUID,
    Boolean,
    Integer,
    Numeric,
    Text,
    Timestamptz,
    Varchar,
    JSONB,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table

from models.base import JSONTable

from models.user import User


class Conversation(JSONTable, tablename="conversations"):
    """A user chat session / conversation."""

    id = UUID(primary_key=True)
    user = UUID(references=User, index=True)
    title = Varchar(length=500, default="New Conversation")
    prompt = Text(default="")
    is_temporary = Boolean(default=False)
    search_enabled = Boolean(default=False)
    threshold = Numeric(digits=(5, 2), null=True, default=None)  # per-chat override
    max_iterations = Integer(null=True, default=None)  # per-chat override
    timeout_seconds = Integer(null=True, default=None)  # per-chat override
    status = Varchar(length=20, default="active")  # active | completed | failed | archived
    best_response = Text(default="")
    best_score = Numeric(digits=(5, 2), default=decimal.Decimal("0"))
    tokens_input = Integer(default=0)
    tokens_output = Integer(default=0)
    metadata = JSONB(default={})
    created_at = Timestamptz(default=TimestamptzNow())
    updated_at = Timestamptz(default=TimestamptzNow())


class ChatAgent(Table, tablename="chat_agents"):
    """AI agent assigned to a conversation (generator)."""

    id = UUID(primary_key=True)
    conversation = UUID(references=Conversation, index=True)
    role = Varchar(length=20, default="generator")  # generator | evaluator
    provider = Varchar(length=50)  # openai | deepseek
    model = Varchar(length=100)  # gpt-5.2, deepseek-3, etc.
    is_active = Boolean(default=True)
    added_mid_chat = Boolean(default=False)
    created_at = Timestamptz(default=TimestamptzNow())


class Iteration(Table, tablename="iterations"):
    """Single generation + evaluation cycle within a conversation."""

    id = UUID(primary_key=True)
    conversation = UUID(references=Conversation, index=True)
    agent = UUID(references=ChatAgent, index=True)
    turn = Integer(default=1)  # which user message (1-based) this answers
    iteration_number = Integer(default=1)
    rephrased_prompt = Text(default="")
    response = Text(default="")
    score = Numeric(digits=(5, 2), default=decimal.Decimal("0"))
    evaluation_reasoning = Text(default="")
    tokens_input = Integer(default=0)
    tokens_output = Integer(default=0)
    timed_out = Boolean(default=False)
    duration_ms = Integer(default=0)
    created_at = Timestamptz(default=TimestamptzNow())


class ChatMessage(JSONTable, tablename="chat_messages"):
    """Audit log / display-friendly message record for a conversation."""

    id = UUID(primary_key=True)
    conversation = UUID(references=Conversation, index=True)
    role = Varchar(length=20)  # user | assistant | system | evaluator
    content = Text(default="")
    agent = UUID(references=ChatAgent, null=True, default=None)
    iteration = UUID(references=Iteration, null=True, default=None)
    score = Numeric(digits=(5, 2), null=True, default=None)
    metadata = JSONB(default={})
    created_at = Timestamptz(default=TimestamptzNow())
