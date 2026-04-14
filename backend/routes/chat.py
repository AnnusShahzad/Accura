"""
Accura – Chat / Conversation Routes
POST   /api/v1/chat                     Create conversation & start orchestration
GET    /api/v1/chat                     List conversations
GET    /api/v1/chat/<id>                Get conversation detail
PATCH  /api/v1/chat/<id>/rename         Rename conversation
POST   /api/v1/chat/<id>/agent          Add agent mid-chat
DELETE /api/v1/chat/<id>                Delete / archive conversation
GET    /api/v1/chat/<id>/iterations     List iterations
GET    /api/v1/chat/<id>/tokens         Token usage for conversation
"""

from __future__ import annotations

import uuid

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from models.chat import ChatAgent, ChatMessage, Conversation, Iteration
from models.settings import UserSettings
from schemas.chat import AddAgentRequest, CreateConversationRequest, FollowUpMessageRequest, RenameConversationRequest
from services.ai_orchestrator import orchestrate_conversation
from services.token_tracker import get_conversation_token_usage
from utils.responses import error, paginated, success

bp = Blueprint("chat", url_prefix="/api/v1/chat")


@bp.post("/")
@require_auth
async def create_conversation(request: Request):
    try:
        body = CreateConversationRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])
    conv_id = str(uuid.uuid4())

    # Create conversation
    await Conversation.insert(
        Conversation(
            id=conv_id,
            user=user_id,
            title=body.title,
            prompt=body.prompt,
            is_temporary=body.is_temporary,
            search_enabled=body.search_enabled,
            threshold=body.threshold,
            max_iterations=body.max_iterations,
            timeout_seconds=body.timeout_seconds,
        )
    ).run()

    # Create generator agent
    await ChatAgent.insert(
        ChatAgent(
            id=str(uuid.uuid4()),
            conversation=conv_id,
            role="generator",
            provider=body.generator_provider,
            model=body.generator_model,
        )
    ).run()

    # Create evaluator agent
    eval_provider = body.evaluator_provider or body.generator_provider
    eval_model = body.evaluator_model or "gpt-5.1"
    await ChatAgent.insert(
        ChatAgent(
            id=str(uuid.uuid4()),
            conversation=conv_id,
            role="evaluator",
            provider=eval_provider,
            model=eval_model,
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
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    offset = (page - 1) * per_page

    conversations = await Conversation.select().where(
        (Conversation.user == user_id)
        & (Conversation.is_temporary == False)
        & (Conversation.status != "archived")
    ).order_by(Conversation.created_at, ascending=False).limit(per_page).offset(offset).run()

    total = await Conversation.count().where(
        (Conversation.user == user_id)
        & (Conversation.is_temporary == False)
        & (Conversation.status != "archived")
    ).run()

    return paginated(conversations, total, page, per_page)


@bp.get("/<conversation_id:str>")
@require_auth
async def get_conversation(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    conv = await Conversation.select().where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).first().run()
    if not conv:
        return error("Conversation not found", status=404)

    agents = await ChatAgent.select().where(
        ChatAgent.conversation == conversation_id
    ).run()

    iterations = await Iteration.select().where(
        Iteration.conversation == conversation_id
    ).order_by(Iteration.iteration_number).run()

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
        body = RenameConversationRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])

    result = await Conversation.update({
        Conversation.title: body.title,
    }).where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).run()

    return success(message="Conversation renamed")


@bp.post("/<conversation_id:str>/agent")
@require_auth
async def add_agent(request: Request, conversation_id: str):
    """Add a new AI agent mid-conversation to generate another response."""
    try:
        body = AddAgentRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])

    conv = await Conversation.select().where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).first().run()
    if not conv:
        return error("Conversation not found", status=404)

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

    # Re-run orchestration with the new agent included
    request.app.add_task(orchestrate_conversation(conversation_id, user_id))

    return success(
        {"agent_id": agent_id},
        message="Agent added – re-processing conversation",
        status=201,
    )


@bp.delete("/<conversation_id:str>")
@require_auth
async def delete_conversation(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    await Conversation.update({
        Conversation.status: "archived",
    }).where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).run()

    return success(message="Conversation deleted")


@bp.get("/<conversation_id:str>/iterations")
@require_auth
async def list_iterations(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    conv = await Conversation.select(Conversation.id).where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).first().run()
    if not conv:
        return error("Conversation not found", status=404)

    iterations = await Iteration.select().where(
        Iteration.conversation == conversation_id
    ).order_by(Iteration.iteration_number).run()

    return success(iterations)


@bp.get("/<conversation_id:str>/tokens")
@require_auth
async def conversation_tokens(request: Request, conversation_id: str):
    user_id = str(request.ctx.user["id"])

    conv = await Conversation.select(Conversation.id).where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).first().run()
    if not conv:
        return error("Conversation not found", status=404)

    usage = await get_conversation_token_usage(conversation_id)
    return success(usage)


@bp.get("/<conversation_id:str>/messages")
@require_auth
async def list_messages(request: Request, conversation_id: str):
    """Return full ordered message history for a conversation."""
    user_id = str(request.ctx.user["id"])

    conv = await Conversation.select(Conversation.id).where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).first().run()
    if not conv:
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
        body = FollowUpMessageRequest(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])

    conv = await Conversation.select().where(
        (Conversation.id == conversation_id) & (Conversation.user == user_id)
    ).first().run()
    if not conv:
        return error("Conversation not found", status=404)
    if conv["status"] == "archived":
        return error("Cannot message an archived conversation", status=400)

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
    await Conversation.update({
        Conversation.prompt: body.prompt,
        Conversation.status: "active",
        Conversation.best_response: "",
        Conversation.best_score: 0,
    }).where(Conversation.id == conversation_id).run()

    # Fire-and-forget new orchestration cycle
    request.app.add_task(orchestrate_conversation(conversation_id, user_id))

    conv = await Conversation.select().where(Conversation.id == conversation_id).first().run()
    return success(conv, message="Follow-up sent – processing", status=201)

