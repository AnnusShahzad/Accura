"""
Accura – Chat / Conversation Routes
POST   /api/v1/chat                     Create conversation & start orchestration
GET    /api/v1/chat                     List conversations
GET    /api/v1/chat/<id>                Get conversation detail
PATCH  /api/v1/chat/<id>/rename         Rename conversation
POST   /api/v1/chat/<id>/agent          Add agent mid-chat
POST   /api/v1/chat/<id>/message        Send a follow-up message
POST   /api/v1/chat/<id>/retry          Re-run the last prompt after a failure
DELETE /api/v1/chat/<id>                Delete conversation
GET    /api/v1/chat/<id>/iterations     List iterations
GET    /api/v1/chat/<id>/messages       List messages
GET    /api/v1/chat/<id>/tokens         Token usage for conversation
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sanic import Blueprint, Request

from config import settings
from middleware.auth_middleware import require_auth
from models.chat import ChatAgent, ChatMessage, Conversation, Iteration
from models.settings import UserSettings
from schemas.chat import AddAgentRequest, CreateConversationRequest, FollowUpMessageRequest, RenameConversationRequest
from services.ai_orchestrator import orchestrate_conversation
from services.token_tracker import get_conversation_token_usage
from utils.responses import error, paginated, success, validation_error, int_arg

bp = Blueprint("chat", url_prefix="/api/v1/chat")


async def _owned_conversation(conversation_id: str, user_id: str) -> dict | None:
    try:
        uuid.UUID(conversation_id)
    except ValueError:
        return None
    return await Conversation.select().where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).first().run()


def _busy(conv: dict):
    return error(
        "A response is still being generated for this conversation. Please wait for it to finish.",
        status=409,
    )


@bp.post("/")
@require_auth
async def create_conversation(request: Request):
    try:
        body = CreateConversationRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])
    conv_id = str(uuid.uuid4())

    prefs = await UserSettings.select(
        UserSettings.preferred_generator_model, UserSettings.preferred_evaluator_model
    ).where(UserSettings.user == user_id).first().run() or {}
    generator_model = (
        body.generator_model
        or prefs.get("preferred_generator_model")
        or settings.get("ai.default_generator_model", "gpt-5.2")
    )
    evaluator_model = (
        body.evaluator_model
        or prefs.get("preferred_evaluator_model")
        or settings.get("ai.default_evaluator_model", "gpt-5.1")
    )

    # Create conversation
    await Conversation.insert(
        Conversation(
            id=conv_id,
            user=user_id,
            title=body.title.strip(),
            prompt=body.prompt,
            is_temporary=body.is_temporary,
            search_enabled=body.search_enabled,
            threshold=body.threshold,
            max_iterations=body.max_iterations,
            timeout_seconds=body.timeout_seconds,
            status="active",
        )
    ).run()

    generator_provider = body.generator_provider or settings.get("ai.default_provider") or "openai"

    # Create generator agent
    await ChatAgent.insert(
        ChatAgent(
            id=str(uuid.uuid4()),
            conversation=conv_id,
            role="generator",
            provider=generator_provider,
            model=generator_model,
        )
    ).run()

    # Create evaluator agent
    await ChatAgent.insert(
        ChatAgent(
            id=str(uuid.uuid4()),
            conversation=conv_id,
            role="evaluator",
            provider=body.evaluator_provider or generator_provider,
            model=evaluator_model,
        )
    ).run()

    # Store user message
    await ChatMessage.insert(
        ChatMessage(
            id=str(uuid.uuid4()),
            conversation=conv_id,
            role="user",
            content=body.prompt,
        )
    ).run()

    # Kick off orchestration (fire-and-forget via add_task)
    request.app.add_task(orchestrate_conversation(conv_id, user_id))

    conv = await Conversation.select().where(Conversation.id == conv_id).first().run()
    return success(conv, message="Conversation created – processing", status=201)


@bp.get("/")
@require_auth
async def list_conversations(request: Request):
    user_id = str(request.ctx.user["id"])
    page = int_arg(request, "page", 1, minimum=1)
    per_page = int_arg(request, "per_page", 20, minimum=1, maximum=100)
    offset = (page - 1) * per_page

    visible = (
        (Conversation.user == user_id)
        & (Conversation.is_temporary == False)  # noqa: E712
        & (Conversation.status != "archived")
    )
    conversations = await Conversation.select(
        Conversation.id,
        Conversation.title,
        Conversation.status,
        Conversation.best_score,
        Conversation.search_enabled,
        Conversation.created_at,
        Conversation.updated_at,
    ).where(visible).order_by(
        Conversation.created_at, ascending=False
    ).limit(per_page).offset(offset).run()

    total = await Conversation.count().where(visible).run()

    return paginated(conversations, total, page, per_page)


@bp.get("/<conversation_id:str>")
@require_auth
async def get_conversation(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    conv = await _owned_conversation(conversation_id, user_id)
    if not conv:
        return error("Conversation not found", status=404)

    agents = await ChatAgent.select().where(
        ChatAgent.conversation == conversation_id
    ).order_by(ChatAgent.created_at).run()

    iterations = await Iteration.select().where(
        Iteration.conversation == conversation_id
    ).order_by(Iteration.created_at).run()

    messages = await ChatMessage.select().where(
        ChatMessage.conversation == conversation_id
    ).order_by(ChatMessage.created_at).run()

    conv["agents"] = agents
    conv["iterations"] = iterations
    conv["messages"] = messages

    return success(conv)


@bp.patch("/<conversation_id:str>/rename")
@require_auth
async def rename_conversation(request: Request, conversation_id: str):
    try:
        body = RenameConversationRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])
    if not await _owned_conversation(conversation_id, user_id):
        return error("Conversation not found", status=404)

    await Conversation.update({
        Conversation.title: body.title.strip(),
        Conversation.updated_at: datetime.now(timezone.utc),
    }).where(Conversation.id == conversation_id).run()

    return success({"id": conversation_id, "title": body.title.strip()}, message="Conversation renamed")


@bp.post("/<conversation_id:str>/agent")
@require_auth
async def add_agent(request: Request, conversation_id: str):
    """Add a new AI agent mid-conversation to generate an alternative response."""
    try:
        body = AddAgentRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])

    conv = await _owned_conversation(conversation_id, user_id)
    if not conv:
        return error("Conversation not found", status=404)
    if conv["status"] == "active":
        return _busy(conv)

    agent_id = str(uuid.uuid4())
    await ChatAgent.insert(
        ChatAgent(
            id=agent_id,
            conversation=conversation_id,
            role=body.role,
            provider=body.provider,
            model=body.model,
            added_mid_chat=True,
        )
    ).run()

    await Conversation.update({Conversation.status: "active"}).where(
        Conversation.id == conversation_id
    ).run()

    # Only the new agent runs; existing answers are kept
    request.app.add_task(orchestrate_conversation(conversation_id, user_id, agent_ids=[agent_id]))

    return success(
        {"agent_id": agent_id},
        message="Agent added – generating an alternative response",
        status=201,
    )


@bp.delete("/<conversation_id:str>")
@require_auth
async def delete_conversation(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    if not await _owned_conversation(conversation_id, user_id):
        return error("Conversation not found", status=404)

    # Children first: they reference the conversation (and each other)
    await ChatMessage.delete().where(ChatMessage.conversation == conversation_id).run()
    await Iteration.delete().where(Iteration.conversation == conversation_id).run()
    await ChatAgent.delete().where(ChatAgent.conversation == conversation_id).run()
    await Conversation.delete().where(Conversation.id == conversation_id).run()

    return success(message="Conversation deleted")


@bp.get("/<conversation_id:str>/iterations")
@require_auth
async def list_iterations(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    if not await _owned_conversation(conversation_id, user_id):
        return error("Conversation not found", status=404)

    iterations = await Iteration.select().where(
        Iteration.conversation == conversation_id
    ).order_by(Iteration.created_at).run()

    return success(iterations)


@bp.get("/<conversation_id:str>/tokens")
@require_auth
async def conversation_tokens(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    if not await _owned_conversation(conversation_id, user_id):
        return error("Conversation not found", status=404)

    usage = await get_conversation_token_usage(conversation_id)
    return success(usage)


@bp.get("/<conversation_id:str>/messages")
@require_auth
async def list_messages(request: Request, conversation_id: str):
    """Return full ordered message history for a conversation."""
    user_id = str(request.ctx.user["id"])

    if not await _owned_conversation(conversation_id, user_id):
        return error("Conversation not found", status=404)

    messages = await ChatMessage.select().where(
        ChatMessage.conversation == conversation_id
    ).order_by(ChatMessage.created_at).run()

    return success(messages)


@bp.post("/<conversation_id:str>/message")
@require_auth
async def send_followup_message(request: Request, conversation_id: str):
    """Append a follow-up user message to an existing conversation and re-run orchestration."""
    try:
        body = FollowUpMessageRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)

    user_id = str(request.ctx.user["id"])

    conv = await _owned_conversation(conversation_id, user_id)
    if not conv:
        return error("Conversation not found", status=404)
    if conv["status"] == "archived":
        return error("Cannot message an archived conversation", status=400)
    if conv["status"] == "active":
        return _busy(conv)

    # Store the new user message
    await ChatMessage.insert(
        ChatMessage(
            id=str(uuid.uuid4()),
            conversation=conversation_id,
            role="user",
            content=body.prompt,
        )
    ).run()

    # Update the conversation prompt to the new message and reset status
    update_data = {
        Conversation.prompt: body.prompt,
        Conversation.status: "active",
        Conversation.best_response: "",
        Conversation.best_score: 0,
        Conversation.updated_at: datetime.now(timezone.utc),
    }
    if body.search_enabled is not None:
        update_data[Conversation.search_enabled] = body.search_enabled

    await Conversation.update(update_data).where(Conversation.id == conversation_id).run()

    # Fire-and-forget new orchestration cycle
    request.app.add_task(orchestrate_conversation(conversation_id, user_id))

    conv = await Conversation.select().where(Conversation.id == conversation_id).first().run()
    return success(conv, message="Follow-up sent – processing", status=201)


@bp.post("/<conversation_id:str>/retry")
@require_auth
async def retry_conversation(request: Request, conversation_id: str):
    """Re-run the latest prompt, e.g. after fixing a missing API key."""
    user_id = str(request.ctx.user["id"])

    conv = await _owned_conversation(conversation_id, user_id)
    if not conv:
        return error("Conversation not found", status=404)
    if conv["status"] == "active":
        return _busy(conv)

    await Conversation.update({
        Conversation.status: "active",
        Conversation.metadata: {},
        Conversation.updated_at: datetime.now(timezone.utc),
    }).where(Conversation.id == conversation_id).run()

    request.app.add_task(orchestrate_conversation(conversation_id, user_id))

    conv = await Conversation.select().where(Conversation.id == conversation_id).first().run()
    return success(conv, message="Retrying", status=202)
