"""
Accura – Generator Agent Service
Generates AI responses to user prompts, optionally calling MCP tools & search.
"""

from __future__ import annotations

import logging
import time
import datetime

from config import settings
from models.admin import SystemPrompt
from services.ai_client import chat_completion
from services.mcp_service import call_mcp_server, get_user_mcp_servers
from services.search_service import google_search

logger = logging.getLogger("accura.generator")

default_system_prompt = "You are a helpful AI assistant. Your Task is to follow User Instructions and Assist them. You have access to tools for search and data retrieval, but only use them if the user explicitly instructs you to or if you determine they are necessary to answer the question. Always try to answer using your own knowledge first before using tools. If The Response requires LaTeX Rendering, Return it in a Pure LaTeX Format!"

async def _get_system_prompt() -> str:
    """Load the generator system prompt (DB first, then YAML fallback)."""
    row = await SystemPrompt.select().where(
        (SystemPrompt.role == "generator") & (SystemPrompt.is_active == True)
    ).first().run()
    if row:
        return row["prompt"]
    return settings.get("ai.system_prompts.generator", default_system_prompt)


async def generate_response(
    user_id: str,
    provider: str,
    model: str,
    prompt: str,
    *,
    search_enabled: bool = False,
    search_query: str | None = None,
    mcp_server_ids: list[str] | None = None,
    timeout_seconds: int = 120,
    max_tokens: int = 4096,
) -> dict:
    """
    Run the generator agent:
      1. Optionally perform search and inject context.
      2. Optionally call MCP servers for tool augmentation.
      3. Call the AI model for completion.

    Returns {
        "response": str,
        "tokens_input": int,
        "tokens_output": int,
        "duration_ms": int,
        "search_results": list,
        "mcp_results": list,
    }
    """
    start = time.monotonic()

    system_prompt = await _get_system_prompt()
    
    # Inject current date awareness
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    date_context = f"Current Date: {date_str}. Use this to evaluate what information is 'recent' or 'latest'."
    
    extra_context_parts: list[str] = [date_context]
    search_results: list[dict] = []
    mcp_results: list[dict] = []

    # --- Search augmentation ---
    if search_enabled and search_query:
        try:
            # Heuristic: if query mentions "latest", "new", current year, etc., restrict to recent results
            recent_keywords = ["new", "latest", "recent", "launch", "released", "update", "2026", "today", "generation", "gen"]
            date_restrict = None
            if any(kw in search_query.lower() for kw in recent_keywords):
                date_restrict = "m3"  # Past 3 months for highly relevant recent info
                logger.info("Applying date restriction 'm3' for query: %s", search_query)
            
            search_results = await google_search(search_query, num_results=5, date_restrict=date_restrict)
            if search_results:
                ctx = "\n".join(
                    f"- [{r['title']}]({r['url']}): {r['snippet']}" for r in search_results
                )
                extra_context_parts.append(f"### Search Results\n{ctx}")
        except Exception:
            logger.warning("Search failed for prompt generation")

    # --- MCP tool augmentation ---
    if mcp_server_ids:
        for server_id in mcp_server_ids:
            try:
                result = await call_mcp_server(server_id, "tools/call", {"prompt": prompt})
                mcp_results.append({"server_id": server_id, "result": result})
                extra_context_parts.append(f"### MCP Tool Output\n{result}")
            except Exception:
                logger.warning("MCP server %s call failed", server_id)

    # --- Build messages ---
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if extra_context_parts:
        messages.append({
            "role": "system",
            "content": "Additional context:\n" + "\n\n".join(extra_context_parts),
        })
    messages.append({"role": "user", "content": prompt})

    # --- Call AI ---
    result = await chat_completion(
        user_id=user_id,
        provider=provider,
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        timeout=timeout_seconds,
    )

    duration_ms = int((time.monotonic() - start) * 1000)

    return {
        "response": result["content"],
        "tokens_input": result["usage"]["prompt_tokens"],
        "tokens_output": result["usage"]["completion_tokens"],
        "duration_ms": duration_ms,
        "search_results": search_results,
        "mcp_results": mcp_results,
    }
