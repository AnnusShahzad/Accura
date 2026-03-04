"""
Accura – Evaluator Agent Service
Scores AI-generated responses against the user prompt.
Returns a satisfaction score (0-100) and reasoning.
"""

from __future__ import annotations

import json
import logging

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
                f"## Original User Prompt\n{original_prompt}\n\n"
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

    # Parse evaluation JSON from model output
    score = 0.0
    reasoning = ""
    try:
        content = result["content"].strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        score = float(parsed.get("score", 0))
        reasoning = str(parsed.get("reasoning", ""))
    except (json.JSONDecodeError, ValueError, IndexError):
        logger.warning("Failed to parse evaluator response: %s", result["content"][:200])
        # Attempt simple numeric extraction as fallback
        import re
        match = re.search(r"(\d{1,3}(?:\.\d+)?)", result["content"])
        if match:
            score = min(float(match.group(1)), 100.0)
        reasoning = result["content"]

    return {
        "score": round(score, 2),
        "reasoning": reasoning,
        "tokens_input": result["usage"]["prompt_tokens"],
        "tokens_output": result["usage"]["completion_tokens"],
    }
