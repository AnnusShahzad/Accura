"""
Accura – Reprompting Service
Rephrases the original user prompt to elicit better AI responses
when the evaluation score is below the threshold.
"""

from __future__ import annotations

import logging

from config import settings
from models.admin import SystemPrompt
from services.ai_client import chat_completion

logger = logging.getLogger("accura.reprompt")


async def _get_system_prompt() -> str:
    row = await SystemPrompt.select().where(
        (SystemPrompt.role == "reprompt") & (SystemPrompt.is_active == True)
    ).first().run()
    if row:
        return row["prompt"]
    return settings.get("ai.system_prompts.reprompt", "")


async def rephrase_prompt(
    user_id: str,
    provider: str,
    model: str,
    original_prompt: str,
    previous_response: str,
    evaluation_reasoning: str,
    score: float,
    *,
    timeout_seconds: int = 60,
) -> dict:
    """
    Rephrase the user's original prompt to get a better response.

    Returns {
        "rephrased_prompt": str,
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
                f"## Original Prompt\n{original_prompt}\n\n"
                f"## Previous AI Response (Score: {score}/100)\n{previous_response}\n\n"
                f"## Evaluator Feedback\n{evaluation_reasoning}\n\n"
                "Please rephrase the original prompt to address the evaluator's feedback "
                "and elicit a better, more comprehensive response. "
                "Return ONLY the rephrased prompt, nothing else."
            ),
        },
    ]

    result = await chat_completion(
        user_id=user_id,
        provider=provider,
        model=model,
        messages=messages,
        temperature=0.5,
        max_tokens=2048,
        timeout=timeout_seconds,
    )

    return {
        "rephrased_prompt": result["content"].strip(),
        "tokens_input": result["usage"]["prompt_tokens"],
        "tokens_output": result["usage"]["completion_tokens"],
    }
