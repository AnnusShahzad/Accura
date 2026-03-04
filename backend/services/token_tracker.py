"""
Accura – Token Tracking Service
Tracks token usage per user, per conversation, per period.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from piccolo.query import Sum

from models.chat import Conversation, Iteration
from models.user import User

logger = logging.getLogger("accura.token_tracker")


async def record_tokens(
    conversation_id: str,
    tokens_input: int,
    tokens_output: int,
) -> None:
    """Increment token counts on a conversation."""
    conv = await Conversation.select().where(Conversation.id == conversation_id).first().run()
    if conv:
        await Conversation.update({
            Conversation.tokens_input: Conversation.tokens_input + tokens_input,
            Conversation.tokens_output: Conversation.tokens_output + tokens_output,
        }).where(Conversation.id == conversation_id).run()


async def get_user_token_usage(
    user_id: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> dict:
    """Aggregate token usage for a user within a date range."""
    query = Iteration.select(
        Sum(Iteration.tokens_input),
        Sum(Iteration.tokens_output),
    ).where(
        Iteration.conversation.is_in(
            Conversation.select(Conversation.id).where(Conversation.user == user_id)
        )
    )

    if period_start:
        query = query.where(Iteration.created_at >= period_start)
    if period_end:
        query = query.where(Iteration.created_at <= period_end)

    result = await query.run()
    row = result[0] if result else {}

    total_input = row.get("sum", 0) or 0
    total_output = row.get("sum", 0) or 0

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "period_start": (period_start or datetime.min).isoformat(),
        "period_end": (period_end or datetime.now(timezone.utc)).isoformat(),
    }


async def get_conversation_token_usage(conversation_id: str) -> dict:
    """Return token usage breakdown for a specific conversation."""
    iterations = await Iteration.select(
        Iteration.id,
        Iteration.iteration_number,
        Iteration.tokens_input,
        Iteration.tokens_output,
    ).where(Iteration.conversation == conversation_id).order_by(Iteration.iteration_number).run()

    total_in = sum(i["tokens_input"] for i in iterations)
    total_out = sum(i["tokens_output"] for i in iterations)

    return {
        "conversation_id": conversation_id,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "iterations": iterations,
    }
