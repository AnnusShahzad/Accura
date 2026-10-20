"""
Accura – Title Generator
Generates a short, descriptive title for a conversation from the user's prompt.
Uses the same chat_completion pattern that generator.py and evaluator.py use.
"""

from __future__ import annotations

import logging
import traceback

from services.ai_client import chat_completion

logger = logging.getLogger("accura.title_generator")

_TITLE_INSTRUCTION = (
    "Based on the user message below, generate a very short title (3-8 words) "
    "that summarizes the TOPIC of the conversation.\n\n"
    "RULES:\n"
    "- Return ONLY the title, nothing else\n"
    "- Do NOT copy/repeat the user's message\n"
    "- No quotes, no punctuation at the end\n"
    "- Summarize the topic, not the question\n\n"
    "EXAMPLES:\n"
    "User: 'What is 2+5 if 3+1=4?' → Basic Arithmetic Questions\n"
    "User: 'Explain quantum computing' → Quantum Computing Overview\n"
    "User: 'Write a Python script to sort' → Python List Sorting Script\n"
    "User: 'I have red rashes on my skin' → Skin Rash Treatment Advice\n\n"
    "Now generate a title for this message:\n"
)


async def generate_title(
    user_id: str,
    provider: str,
    model: str,
    prompt: str,
) -> str:
    """Return an auto-generated title for a conversation."""

    logger.info(
        "Title gen starting: provider=%s model=%s prompt_len=%d",
        provider, model, len(prompt),
    )

    # Build a single user message (more compatible across providers)
    user_content = _TITLE_INSTRUCTION + prompt[:500]

    try:
        result = await chat_completion(
            user_id=user_id,
            provider=provider,
            model=model,
            messages=[
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=100,
            timeout=60,
        )

        raw = result["content"]
        logger.info("Title gen raw response: %r", raw)

        # Clean up response
        title = raw.strip()
        # Remove common wrapping
        for ch in ['"', "'", ".", "*", "#"]:
            title = title.strip(ch)
        title = title.strip()

        # Take only the first line if multi-line
        if "\n" in title:
            title = title.split("\n")[0].strip()

        # Remove "Title:" prefix if model added it
        for prefix in ["Title:", "title:", "TITLE:"]:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()

        logger.info("Title gen cleaned: %r", title)

        if title and len(title) < 200:
            return title[:500]

        logger.warning("Title gen result rejected (empty or too long)")

    except Exception as exc:
        logger.error(
            "Title gen FAILED: %s: %s\n%s",
            type(exc).__name__, exc, traceback.format_exc(),
        )

    return fallback_title(prompt)


def fallback_title(prompt: str) -> str:
    """First few words of the prompt, used when no model title is available."""
    words = prompt.strip().split()
    if len(words) > 8:
        return " ".join(words[:8]) + "..."
    return prompt.strip()[:200] or "New Conversation"
