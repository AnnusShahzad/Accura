"""
Accura – Token Tracking Service
Tracks token usage per user, per conversation, per period.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from models.chat import Conversation, Iteration

logger = logging.getLogger("accura.token_tracker")


async def record_tokens(
    conversation_id: str,
    tokens_input: int,
    tokens_output: int,
) -> None:
    """Increment token counts on a conversation."""
    if tokens_input or tokens_output:
        await Conversation.update({
            Conversation.tokens_input: Conversation.tokens_input + tokens_input,
            Conversation.tokens_output: Conversation.tokens_output + tokens_output,
        }).where(Conversation.id == conversation_id).run()


async def get_user_token_usage(
    user_id: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> dict:
    """Aggregate token usage for a user within a date range.

    Iterations are the source of truth: each one records the tokens spent
    generating, evaluating and rephrasing in that round.
    """
    query = Iteration.select(
        Iteration.conversation,
        Iteration.tokens_input,
        Iteration.tokens_output,
    ).where(
        Iteration.conversation.is_in(
            Conversation.select(Conversation.id).where(Conversation.user == user_id)
        )
    )
    if period_start:
        query = query.where(Iteration.created_at >= period_start)
    if period_end:
        query = query.where(Iteration.created_at <= period_end)
    rows = await query.run()

    per_conv: dict[str, dict] = {}
    for row in rows:
        key = str(row["conversation"])
        entry = per_conv.setdefault(key, {"tokens_input": 0, "tokens_output": 0})
        entry["tokens_input"] += row["tokens_input"] or 0
        entry["tokens_output"] += row["tokens_output"] or 0

    breakdown = []
    if per_conv:
        convs = await Conversation.select(
            Conversation.id, Conversation.title, Conversation.created_at
        ).where(Conversation.id.is_in(list(per_conv))).run()
        for conv in convs:
            usage = per_conv[str(conv["id"])]
            breakdown.append({
                "conversation_id": str(conv["id"]),
                "title": conv["title"],
                "created_at": conv["created_at"],
                **usage,
            })
        breakdown.sort(key=lambda b: b["tokens_input"] + b["tokens_output"], reverse=True)

    total_input = sum(u["tokens_input"] for u in per_conv.values())
    total_output = sum(u["tokens_output"] for u in per_conv.values())

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "period_start": (period_start or datetime(1970, 1, 1, tzinfo=timezone.utc)).isoformat(),
        "period_end": (period_end or datetime.now(timezone.utc)).isoformat(),
        "breakdown": breakdown[:50],
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
