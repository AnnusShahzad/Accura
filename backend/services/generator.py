"""
Accura – Generator Agent Service
Generates AI responses to user prompts, optionally calling MCP tools & search.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
import time

from config import settings
from models.admin import SystemPrompt
from services.ai_client import chat_completion
from services.mcp_service import call_mcp_tool
from services.search_service import google_search

logger = logging.getLogger("accura.generator")

default_system_prompt = "You are a helpful AI assistant. Your Task is to follow User Instructions and Assist them. You have access to tools for search and data retrieval, but only use them if the user explicitly instructs you to or if you determine they are necessary to answer the question. Always try to answer using your own knowledge first before using tools. If The Response requires LaTeX Rendering, Return it in a Pure LaTeX Format!"

# Words that suggest the user wants fresh information, so search results
# get restricted to the last few months. Matched as whole words: a plain
# substring test made "gen" match "general" and "new" match "renewable".
_RECENT_PATTERN = re.compile(
    r"\b(new|newest|latest|recent|recently|launch(ed)?|release[sd]?|update[sd]?|"
    r"today|this (week|month|year)|current(ly)?|\d{4} (model|version|release))\b",
    re.IGNORECASE,
)


async def _get_system_prompt() -> str:
    """Load the generator system prompt (DB first, then YAML fallback)."""
    row = await SystemPrompt.select().where(
        (SystemPrompt.role == "generator") & (SystemPrompt.is_active == True)  # noqa: E712
    ).first().run()
    if row:
        return row["prompt"]
    return settings.get("ai.system_prompts.generator", default_system_prompt)


def _wants_recent(query: str) -> bool:
    if _RECENT_PATTERN.search(query):
        return True
    year = datetime.datetime.now().year
    return str(year) in query or str(year - 1) in query


async def generate_response(
    user_id: str,
    provider: str,
    model: str,
    prompt: str,
    *,
    history: list[dict] | None = None,
    search_enabled: bool = False,
    search_query: str | None = None,
    mcp_tools: list[dict] | None = None,
    timeout_seconds: int = 120,
    max_tokens: int = 4096,
) -> dict:
    """
    Run the generator agent:
      1. Optionally perform search and inject context.
      2. Call the AI model; if MCP tools are available the model may call
         them, and the results are fed back until it answers.

    ``history`` is the earlier conversation as [{"role", "content"}].
    ``mcp_tools`` comes from mcp_service.discover_tools().

    Returns {
        "response": str,
        "tokens_input": int,
        "tokens_output": int,
        "duration_ms": int,
        "search_results": list,
        "tool_calls": list,
    }
    """
    start = time.monotonic()

    system_prompt = await _get_system_prompt()

    # Inject current date awareness
    date_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
    extra_context_parts: list[str] = [
        f"Current Date: {date_str}. Use this to evaluate what information is 'recent' or 'latest'."
    ]
    search_results: list[dict] = []
    tool_log: list[dict] = []

    # --- Search augmentation ---
    if search_enabled and search_query:
        try:
            date_restrict = "m3" if _wants_recent(search_query) else None
            search_results = await google_search(search_query, num_results=5, date_restrict=date_restrict)
            if search_results:
                ctx = "\n".join(
                    f"- [{r['title']}]({r['url']}): {r['snippet']}" for r in search_results
                )
                extra_context_parts.append(
                    "### Web Search Results\nCite sources as markdown links when you use them.\n" + ctx
                )
        except Exception:
            logger.warning("Search failed for prompt generation", exc_info=True)

    # --- Build messages ---
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": "Additional context:\n" + "\n\n".join(extra_context_parts)},
    ]
    for turn in history or []:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": prompt})

    tools = [t["spec"] for t in mcp_tools or []]
    by_name = {t["spec"]["function"]["name"]: t for t in mcp_tools or []}
    max_rounds = int(settings.get("ai.max_tool_rounds", 5))

    tokens_in = 0
    tokens_out = 0
    content = ""
    for round_num in range(max_rounds + 1):
        # On the last round, withhold tools so the model must answer.
        offer_tools = tools if tools and round_num < max_rounds else None
        result = await chat_completion(
            user_id=user_id,
            provider=provider,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            timeout=timeout_seconds,
            tools=offer_tools,
        )
        tokens_in += result["usage"]["prompt_tokens"]
        tokens_out += result["usage"]["completion_tokens"]
        content = result["content"]

        if not result["tool_calls"] or not offer_tools:
            break

        messages.append({
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in result["tool_calls"]
            ],
        })
        for tc in result["tool_calls"]:
            tool = by_name.get(tc["name"])
            try:
                args = json.loads(tc["arguments"] or "{}")
                if not isinstance(args, dict):
                    raise ValueError("arguments must be an object")
                if tool is None:
                    raise ValueError(f"unknown tool {tc['name']}")
                output = await call_mcp_tool(tool["server_id"], tool["tool_name"], args)
            except Exception as exc:
                logger.warning("MCP tool %s failed: %s", tc["name"], exc)
                output = f"Tool call failed: {exc}"
            tool_log.append({
                "tool": tool["tool_name"] if tool else tc["name"],
                "server_id": tool["server_id"] if tool else None,
                "output_preview": output[:500],
            })
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": output[:20000]})

    duration_ms = int((time.monotonic() - start) * 1000)

    return {
        "response": content,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "duration_ms": duration_ms,
        "search_results": search_results,
        "tool_calls": tool_log,
    }
