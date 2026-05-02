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
from typing import Any

from config import settings
from models.chat import ChatAgent, Conversation, Iteration, ChatMessage
from models.settings import UserSettings
from services.evaluator import evaluate_response
from services.generator import generate_response
from services.reprompt import rephrase_prompt
from services.token_tracker import record_tokens
from services.notification_service import send_notification
from utils.exceptions import TimeoutError as AccuraTimeout

logger = logging.getLogger("accura.orchestrator")


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


async def _run_single_agent_loop(
    user_id: str,
    conversation_id: str,
    agent: dict,
    prompt: str,
    eval_provider: str,
    eval_model: str,
    resolved: dict,
    search_enabled: bool = False,
    mcp_server_ids: list[str] | None = None,
) -> dict:
    """Execute the generate → evaluate → rephrase loop for one agent."""

    threshold = resolved["threshold"]
    max_iterations = resolved["max_iterations"]
    timeout_seconds = resolved["timeout_seconds"]

    current_prompt = prompt
    best_response = ""
    best_score = 0.0
    total_tokens_in = 0
    total_tokens_out = 0

    for iteration_num in range(1, max_iterations + 1):
        logger.info(
            "Conversation %s | Agent %s | Iteration %d/%d",
            conversation_id, agent["id"], iteration_num, max_iterations,
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
                    search_enabled=search_enabled,
                    search_query=prompt if search_enabled else None,
                    mcp_server_ids=mcp_server_ids,
                    timeout_seconds=timeout_seconds,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Agent %s timed out on iteration %d", agent["id"], iteration_num)
            gen_result = {
                "response": best_response or "(timed out – no response)",
                "tokens_input": 0,
                "tokens_output": 0,
                "duration_ms": timeout_seconds * 1000,
            }
            timed_out = True

        response_text = gen_result["response"]
        total_tokens_in += gen_result["tokens_input"]
        total_tokens_out += gen_result["tokens_output"]

        # --- Evaluate ---
        eval_result = await evaluate_response(
            user_id=user_id,
            provider=eval_provider,
            model=eval_model,
            original_prompt=prompt,
            ai_response=response_text,
            timeout_seconds=timeout_seconds,
        )
        total_tokens_in += eval_result["tokens_input"]
        total_tokens_out += eval_result["tokens_output"]

        score = eval_result["score"]
        reasoning = eval_result["reasoning"]

        # --- Store iteration ---
        iter_id = str(uuid.uuid4())
        await Iteration.insert(
            Iteration(
                id=iter_id,
                conversation=conversation_id,
                agent=agent["id"],
                iteration_number=iteration_num,
                rephrased_prompt=current_prompt if iteration_num > 1 else "",
                response=response_text,
                score=score,
                evaluation_reasoning=reasoning,
                tokens_input=gen_result["tokens_input"],
                tokens_output=gen_result["tokens_output"],
                timed_out=timed_out,
                duration_ms=gen_result.get("duration_ms", 0),
            )
        ).run()

        if score > best_score:
            best_score = score
            best_response = response_text

        # --- Emit live progress into conversation metadata ---
        await Conversation.update({
            Conversation.metadata: {
                "current_iteration": iteration_num,
                "current_best_score": round(float(best_score), 2),
                "max_iterations": max_iterations,
            },
        }).where(Conversation.id == conversation_id).run()

        # --- Check threshold ---
        if score >= threshold:
            logger.info("Threshold met: %.2f >= %.2f", score, threshold)
            break

        if timed_out:
            break

        # --- Rephrase for next iteration ---
        if iteration_num < max_iterations:
            reprompt_model = settings.get("ai.default_reprompt_model", eval_model)
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
            current_prompt = reprompt_result["rephrased_prompt"]
            total_tokens_in += reprompt_result["tokens_input"]
            total_tokens_out += reprompt_result["tokens_output"]

    return {
        "agent_id": agent["id"],
        "best_response": best_response,
        "best_score": best_score,
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
    }


async def orchestrate_conversation(
    conversation_id: str,
    user_id: str,
) -> dict:
    """
    Main orchestration entry-point for a conversation.
    Runs all generator agents in parallel, evaluates, and picks the best.
    """

    conversation = await Conversation.select().where(
        Conversation.id == conversation_id
    ).first().run()
    if not conversation:
        raise ValueError("Conversation not found")

    resolved = await _resolve_settings(user_id, conversation)

    # Fetch all active generator agents
    agents = await ChatAgent.select().where(
        (ChatAgent.conversation == conversation_id)
        & (ChatAgent.role == "generator")
        & (ChatAgent.is_active == True)
    ).run()
    if not agents:
        raise ValueError("No generator agents configured for this conversation")

    # Get evaluator agent config
    evaluator_agent = await ChatAgent.select().where(
        (ChatAgent.conversation == conversation_id)
        & (ChatAgent.role == "evaluator")
    ).first().run()
    eval_provider = evaluator_agent["provider"] if evaluator_agent else "openai"
    eval_model = evaluator_agent["model"] if evaluator_agent else settings.get("ai.default_evaluator_model", "gpt-5.1")

    # Get user MCP servers
    from services.mcp_service import get_user_mcp_servers
    mcp_servers = await get_user_mcp_servers(user_id)
    mcp_ids = [str(s["id"]) for s in mcp_servers]

    # Run all agents in parallel
    tasks = [
        _run_single_agent_loop(
            user_id=user_id,
            conversation_id=conversation_id,
            agent=agent,
            prompt=conversation["prompt"],
            eval_provider=eval_provider,
            eval_model=eval_model,
            resolved=resolved,
            search_enabled=conversation.get("search_enabled", False),
            mcp_server_ids=mcp_ids if mcp_ids else None,
        )
        for agent in agents
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Pick best result
    best_overall: dict[str, Any] = {"best_response": "", "best_score": 0.0}
    total_in = 0
    total_out = 0

    for r in results:
        if isinstance(r, Exception):
            logger.error("Agent loop failed: %s", r)
            continue
        total_in += r["total_tokens_in"]
        total_out += r["total_tokens_out"]
        if r["best_score"] > best_overall["best_score"]:
            best_overall = r

    # Update conversation
    await Conversation.update({
        Conversation.best_response: best_overall["best_response"],
        Conversation.best_score: best_overall["best_score"],
        Conversation.tokens_input: total_in,
        Conversation.tokens_output: total_out,
        Conversation.status: "completed",
    }).where(Conversation.id == conversation_id).run()

    await record_tokens(conversation_id, total_in, total_out)

    # Store final assistant message
    await ChatMessage.insert(
        ChatMessage(
            id=str(uuid.uuid4()),
            conversation=conversation_id,
            role="assistant",
            content=best_overall["best_response"],
            score=best_overall["best_score"],
            metadata={"agent_id": best_overall.get("agent_id", "")},
        )
    ).run()

    # Notify user
    await send_notification(
        user_id=user_id,
        title="Response Ready",
        body=f"Your conversation has completed with a score of {best_overall['best_score']:.1f}%",
        metadata={"conversation_id": conversation_id},
    )

    # Auto-generate title if user didn't provide one
    current_title = conversation.get("title", "")
    logger.info("Current title for %s: %r", conversation_id, current_title)
    if current_title in ("", "New Conversation"):
        from services.title_generator import generate_title

        # Use the first generator agent (proven to work - it produced the response)
        gen_agent = agents[0] if agents else None
        title_provider = gen_agent["provider"] if gen_agent else eval_provider
        title_model = gen_agent["model"] if gen_agent else eval_model

        try:
            auto_title = await generate_title(
                user_id, title_provider, title_model, conversation["prompt"]
            )
            logger.info("Auto-generated title for %s: %r", conversation_id, auto_title)
            await Conversation.update({
                Conversation.title: auto_title,
            }).where(Conversation.id == conversation_id).run()
        except Exception:
            logger.exception("Auto title generation failed for %s", conversation_id)

    return {
        "conversation_id": conversation_id,
        "best_response": best_overall["best_response"],
        "best_score": best_overall["best_score"],
        "tokens_input": total_in,
        "tokens_output": total_out,
        "status": "completed",
    }

