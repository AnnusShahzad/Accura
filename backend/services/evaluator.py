"""
Accura – Evaluator Agent Service
Scores AI-generated responses against the user prompt.
Returns a satisfaction score (0-100) and reasoning.
"""

from __future__ import annotations

import json
import logging
import re

from config import settings
from models.admin import SystemPrompt
from services.ai_client import chat_completion

logger = logging.getLogger("accura.evaluator")


async def _get_system_prompt() -> str:
    row = await SystemPrompt.select().where(
        (SystemPrompt.role == "evaluator") & (SystemPrompt.is_active == True)
    ).first().run()
    if row:
        return row["prompt"]
    return settings.get("ai.system_prompts.evaluator", "")


async def evaluate_response(
    user_id: str,
    provider: str,
    model: str,
    original_prompt: str,
    ai_response: str,
    *,
    context: str = "",
    timeout_seconds: int = 60,
) -> dict:
    """
    Evaluate an AI response.

    Returns {
        "score": float (0-100),
        "reasoning": str,
        "tokens_input": int,
        "tokens_output": int,
    }
    """
    system_prompt = await _get_system_prompt()

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                (f"## Earlier Conversation (for context)\n{context}\n\n" if context else "")
                + f"## Original User Prompt\n{original_prompt}\n\n"
                f"## AI Response\n{ai_response}\n\n"
                "Evaluate the response. Return JSON: {\"score\": <0-100>, \"reasoning\": \"<brief>\"}"
            ),
        },
    ]

    result = await chat_completion(
        user_id=user_id,
        provider=provider,
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=1024,
        timeout=timeout_seconds,
    )

    score, reasoning = parse_evaluation(result["content"])

    return {
        "score": round(score, 2),
        "reasoning": reasoning,
        "tokens_input": result["usage"]["prompt_tokens"],
        "tokens_output": result["usage"]["completion_tokens"],
    }


def parse_evaluation(raw: str) -> tuple[float, str]:
    """Extract (score, reasoning) from an evaluator reply.

    Models wrap JSON in prose or code fences, use "Score: 82/100", or
    answer on a 0-10 scale; handle the common shapes and clamp to 0-100.
    """
    content = (raw or "").strip()
    candidates = [content]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1))
    braced = re.search(r"\{.*\}", content, re.DOTALL)
    if braced:
        candidates.append(braced.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict) and "score" in parsed:
            try:
                score = float(parsed["score"])
            except (TypeError, ValueError):
                continue
            return max(0.0, min(score, 100.0)), str(parsed.get("reasoning", ""))

    logger.warning("Evaluator reply was not JSON: %s", content[:200])
    match = re.search(r"score\D{0,10}(\d{1,3}(?:\.\d+)?)\s*(/\s*(10|100))?", content, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*(/\s*(10|100))?", content)
    score = 0.0
    if match:
        score = float(match.group(1))
        if match.group(3) == "10":
            score *= 10
    return max(0.0, min(score, 100.0)), content
