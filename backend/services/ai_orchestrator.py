"""
Accura – AI Orchestrator
The main control loop: generate → evaluate → (rephrase → re-generate → re-evaluate …)
until the threshold is met or max iterations reached.
Supports multiple generator agents per conversation.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from config import settings
from models.chat import ChatAgent, ChatMessage, Conversation, Iteration
from models.settings import UserSettings
from services.evaluator import evaluate_response
from services.generator import generate_response
from services.reprompt import rephrase_prompt
from services.token_tracker import record_tokens
from services.notification_service import send_notification

logger = logging.getLogger("accura.orchestrator")

# How much earlier conversation is replayed to the models
_HISTORY_MESSAGES = 10
_HISTORY_CHARS = 4000


async def _resolve_settings(user_id: str, conversation: dict) -> dict:
    """Merge global user settings with per-conversation overrides."""
    user_settings = await UserSettings.select().where(
        UserSettings.user == user_id
    ).first().run()

    defaults = {
        "threshold": float(settings.get("evaluation.global_threshold", 75)),
        "max_iterations": int(settings.get("evaluation.default_max_iterations", 5)),
        "timeout_seconds": int(settings.get("evaluation.default_timeout_seconds", 120)),
    }

    if user_settings:
        defaults["threshold"] = float(user_settings.get("global_threshold", defaults["threshold"]))
        defaults["max_iterations"] = int(user_settings.get("max_iterations", defaults["max_iterations"]))
        defaults["timeout_seconds"] = int(user_settings.get("timeout_seconds", defaults["timeout_seconds"]))

    # Per-conversation overrides take highest priority
    if conversation.get("threshold") is not None:
        defaults["threshold"] = float(conversation["threshold"])
    if conversation.get("max_iterations") is not None:
        defaults["max_iterations"] = int(conversation["max_iterations"])
    if conversation.get("timeout_seconds") is not None:
        defaults["timeout_seconds"] = int(conversation["timeout_seconds"])

    return defaults


async def _load_history(conversation_id: str) -> tuple[list[dict], int]:
    """Return (earlier user/assistant turns, current turn number).

    The newest user message is the prompt being answered, so it is left
    out of the history.
    """
    messages = await ChatMessage.select(
        ChatMessage.role, ChatMessage.content
    ).where(
        (ChatMessage.conversation == conversation_id)
        & (ChatMessage.role.is_in(["user", "assistant"]))
    ).order_by(ChatMessage.created_at).run()

    turn = sum(1 for m in messages if m["role"] == "user") or 1
    if messages and messages[-1]["role"] == "user":
        messages = messages[:-1]
    history = [m for m in messages if m["content"]][-_HISTORY_MESSAGES:]

    # Keep the replay bounded: trim the oldest messages first.
    while history and sum(len(m["content"]) for m in history) > _HISTORY_CHARS * 2:
        history.pop(0)
    return history, turn


def _history_as_text(history: list[dict]) -> str:
    text = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
    return text[-_HISTORY_CHARS:]


async def _publish_progress(conversation_id: str, progress: dict) -> None:
    await Conversation.update({
        Conversation.metadata: dict(progress),
        Conversation.updated_at: datetime.now(timezone.utc),
    }).where(Conversation.id == conversation_id).run()


async def _run_single_agent_loop(
    user_id: str,
    conversation_id: str,
    agent: dict,
    prompt: str,
    eval_provider: str,
    eval_model: str,
    resolved: dict,
    *,
    turn: int,
    history: list[dict],
    progress: dict,
    search_enabled: bool = False,
    mcp_tools: list[dict] | None = None,
) -> dict:
    """Execute the generate → evaluate → rephrase loop for one agent."""

    threshold = resolved["threshold"]
    max_iterations = resolved["max_iterations"]
    timeout_seconds = resolved["timeout_seconds"]
    context = _history_as_text(history)

    current_prompt = prompt
    best_response = ""
    best_score = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    last_error: str | None = None

    for iteration_num in range(1, max_iterations + 1):
        logger.info(
            "Conversation %s | Agent %s | Turn %d | Iteration %d/%d",
            conversation_id, agent["id"], turn, iteration_num, max_iterations,
        )

        # --- Generate ---
        timed_out = False
        try:
            gen_result = await asyncio.wait_for(
                generate_response(
                    user_id=user_id,
                    provider=agent["provider"],
                    model=agent["model"],
                    prompt=current_prompt,
                    history=history,
                    search_enabled=search_enabled,
                    search_query=prompt if search_enabled else None,
                    mcp_tools=mcp_tools,
                    timeout_seconds=timeout_seconds,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Agent %s timed out on iteration %d", agent["id"], iteration_num)
            gen_result = {
                "response": "",
                "tokens_input": 0,
                "tokens_output": 0,
                "duration_ms": timeout_seconds * 1000,
            }
            timed_out = True
            last_error = f"{agent['model']} timed out after {timeout_seconds}s"

        response_text = gen_result["response"]
        iter_tokens_in = gen_result["tokens_input"]
        iter_tokens_out = gen_result["tokens_output"]

        # --- Evaluate (nothing to evaluate after a timeout) ---
        score = 0.0
        reasoning = "Generation timed out." if timed_out else ""
        if response_text.strip():
            eval_result = await evaluate_response(
                user_id=user_id,
                provider=eval_provider,
                model=eval_model,
                original_prompt=prompt,
                ai_response=response_text,
                context=context,
                timeout_seconds=timeout_seconds,
            )
            iter_tokens_in += eval_result["tokens_input"]
            iter_tokens_out += eval_result["tokens_output"]
            score = eval_result["score"]
            reasoning = eval_result["reasoning"]
        elif not timed_out:
            reasoning = "The model returned an empty response."

        if score > best_score or (not best_response and response_text):
            best_score = max(best_score, score)
            best_response = response_text

        progress["current_iteration"] = max(progress.get("current_iteration", 0), iteration_num)
        progress["current_best_score"] = round(max(progress.get("current_best_score", 0.0), best_score), 2)

        # --- Rephrase for next iteration ---
        done = score >= threshold or timed_out or iteration_num >= max_iterations
        if done and score >= threshold:
            logger.info("Threshold met: %.2f >= %.2f", score, threshold)
        next_prompt = current_prompt
        if not done:
            reprompt_model = settings.get("ai.default_reprompt_model") or eval_model
            reprompt_result = await rephrase_prompt(
                user_id=user_id,
                provider=eval_provider,
                model=reprompt_model,
                original_prompt=prompt,
                previous_response=response_text,
                evaluation_reasoning=reasoning,
                score=score,
                timeout_seconds=timeout_seconds,
            )
            next_prompt = reprompt_result["rephrased_prompt"] or current_prompt
            iter_tokens_in += reprompt_result["tokens_input"]
            iter_tokens_out += reprompt_result["tokens_output"]

        # --- Store iteration (tokens = generate + evaluate + rephrase) ---
        await Iteration.insert(
            Iteration(
                id=str(uuid.uuid4()),
                conversation=conversation_id,
                agent=agent["id"],
                turn=turn,
                iteration_number=iteration_num,
                rephrased_prompt=current_prompt if iteration_num > 1 else "",
                response=response_text,
                score=score,
                evaluation_reasoning=reasoning,
                tokens_input=iter_tokens_in,
                tokens_output=iter_tokens_out,
                timed_out=timed_out,
                duration_ms=gen_result.get("duration_ms", 0),
            )
        ).run()
        total_tokens_in += iter_tokens_in
        total_tokens_out += iter_tokens_out
        await _publish_progress(conversation_id, progress)

        if done:
            break
        current_prompt = next_prompt

    if not best_response and last_error:
        raise RuntimeError(last_error)

    return {
        "agent_id": str(agent["id"]),
        "model": agent["model"],
        "best_response": best_response,
        "best_score": best_score,
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
    }


async def _mark_failed(conversation_id: str, user_id: str, reason: str) -> None:
    logger.error("Conversation %s failed: %s", conversation_id, reason)
    # Message first, status second (clients stop polling on the status)
    await ChatMessage.insert(
        ChatMessage(
            id=str(uuid.uuid4()),
            conversation=conversation_id,
            role="system",
            content=reason,
            metadata={"type": "error"},
        )
    ).run()
    await Conversation.update({
        Conversation.status: "failed",
        Conversation.metadata: {"error": reason},
        Conversation.updated_at: datetime.now(timezone.utc),
    }).where(Conversation.id == conversation_id).run()
    await send_notification(
        user_id=user_id,
        title="Response Failed",
        body=reason,
        metadata={"conversation_id": conversation_id},
    )


async def orchestrate_conversation(
    conversation_id: str,
    user_id: str,
    agent_ids: list[str] | None = None,
) -> dict | None:
    """
    Main orchestration entry-point for a conversation.

    Runs all active generator agents in parallel (or only *agent_ids*,
    e.g. an agent added mid-chat), evaluates, and stores the best
    answer. Any failure leaves the conversation in status "failed" with
    a readable reason instead of spinning in "active" forever.
    """
    try:
        return await _orchestrate(conversation_id, user_id, agent_ids)
    except Exception as exc:
        logger.exception("Orchestration crashed for %s", conversation_id)
        reason = getattr(exc, "message", None) or str(exc) or type(exc).__name__
        try:
            still_exists = await Conversation.exists().where(Conversation.id == conversation_id).run()
            if still_exists:  # it may have been deleted mid-run
                await _mark_failed(conversation_id, user_id, reason)
        except Exception:
            logger.exception("Could not record failure for %s", conversation_id)
        return None


async def _orchestrate(conversation_id: str, user_id: str, agent_ids: list[str] | None) -> dict:
    conversation = await Conversation.select().where(
        Conversation.id == conversation_id
    ).first().run()
    if not conversation:
        raise ValueError("Conversation not found")

    resolved = await _resolve_settings(user_id, conversation)
    history, turn = await _load_history(conversation_id)

    # Fetch generator agents
    query = ChatAgent.select().where(
        (ChatAgent.conversation == conversation_id)
        & (ChatAgent.role == "generator")
        & (ChatAgent.is_active == True)  # noqa: E712
    ).order_by(ChatAgent.created_at)
    agents = await query.run()
    if agent_ids:
        agents = [a for a in agents if str(a["id"]) in set(agent_ids)]
    if not agents:
        raise ValueError("No generator agents configured for this conversation")

    # Get evaluator agent config
    evaluator_agent = await ChatAgent.select().where(
        (ChatAgent.conversation == conversation_id)
        & (ChatAgent.role == "evaluator")
    ).first().run()
    eval_provider = evaluator_agent["provider"] if evaluator_agent else "openai"
    eval_model = evaluator_agent["model"] if evaluator_agent else settings.get("ai.default_evaluator_model", "gpt-5.1")

    # MCP tools are discovered once per run and shared by every agent
    from services.mcp_service import discover_tools, get_user_mcp_servers

    mcp_tools = await discover_tools(await get_user_mcp_servers(user_id))

    progress: dict[str, Any] = {
        "turn": turn,
        "current_iteration": 0,
        "current_best_score": 0.0,
        "max_iterations": resolved["max_iterations"],
        "threshold": resolved["threshold"],
        "agents": len(agents),
    }
    await _publish_progress(conversation_id, progress)

    results = await asyncio.gather(
        *[
            _run_single_agent_loop(
                user_id=user_id,
                conversation_id=conversation_id,
                agent=agent,
                prompt=conversation["prompt"],
                eval_provider=eval_provider,
                eval_model=eval_model,
                resolved=resolved,
                turn=turn,
                history=history,
                progress=progress,
                search_enabled=bool(conversation.get("search_enabled", False)),
                mcp_tools=mcp_tools or None,
            )
            for agent in agents
        ],
        return_exceptions=True,
    )

    # Pick best result
    successes = [r for r in results if not isinstance(r, BaseException)]
    failures = [r for r in results if isinstance(r, BaseException)]
    for f in failures:
        logger.error("Agent loop failed: %s", f)

    total_in = sum(r["total_tokens_in"] for r in successes)
    total_out = sum(r["total_tokens_out"] for r in successes)
    await record_tokens(conversation_id, total_in, total_out)

    usable = [r for r in successes if r["best_response"]]
    if not usable:
        first = failures[0] if failures else None
        reason = (getattr(first, "message", None) or str(first)) if first else ""
        raise RuntimeError(reason or "No agent produced a response")

    best = max(usable, key=lambda r: r["best_score"])
    is_alternative = bool(agent_ids)

    # A mid-chat agent only replaces the stored best answer if it beats it
    current_best = float(conversation.get("best_score") or 0)
    if not is_alternative or best["best_score"] > current_best:
        await Conversation.update({
            Conversation.best_response: best["best_response"],
            Conversation.best_score: best["best_score"],
        }).where(Conversation.id == conversation_id).run()

    # Store final assistant message
    await ChatMessage.insert(
        ChatMessage(
            id=str(uuid.uuid4()),
            conversation=conversation_id,
            role="assistant",
            content=best["best_response"],
            score=best["best_score"],
            metadata={
                "agent_id": best["agent_id"],
                "model": best["model"],
                "turn": turn,
                "alternative": is_alternative,
                "failed_agents": len(failures),
            },
        )
    ).run()

    # Auto-generate title if user didn't provide one
    title_text = conversation.get("title") or ""
    if turn == 1 and not is_alternative and (conversation.get("title") or "") in ("", "New Conversation"):
        from services.title_generator import generate_title

        try:
            auto_title = await generate_title(
                user_id, agents[0]["provider"], agents[0]["model"], conversation["prompt"]
            )
            await Conversation.update({
                Conversation.title: auto_title,
            }).where(Conversation.id == conversation_id).run()
            title_text = auto_title
        except Exception:
            logger.exception("Auto title generation failed for %s", conversation_id)

    # Flip the status last: clients stop polling once they see it, so the
    # answer and the title must already be in place.
    progress["current_best_score"] = round(best["best_score"], 2)
    await Conversation.update({
        Conversation.status: "completed",
        Conversation.metadata: progress,
        Conversation.updated_at: datetime.now(timezone.utc),
    }).where(Conversation.id == conversation_id).run()

    # Notify user
    await send_notification(
        user_id=user_id,
        title="Response Ready",
        body=f"\"{title_text or 'Your conversation'}\" completed with a score of {best['best_score']:.1f}%",
        metadata={"conversation_id": conversation_id},
    )

    return {
        "conversation_id": conversation_id,
        "best_response": best["best_response"],
        "best_score": best["best_score"],
        "tokens_input": total_in,
        "tokens_output": total_out,
        "status": "completed",
    }
