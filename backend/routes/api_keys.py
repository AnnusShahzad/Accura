"""
Accura – API Key (BYOK) Routes
POST   /api/v1/api-keys
GET    /api/v1/api-keys
PUT    /api/v1/api-keys/<id>
DELETE /api/v1/api-keys/<id>
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sanic import Blueprint, Request

from middleware.auth_middleware import require_auth
from models.api_key import UserAPIKey
from schemas.api_key import CreateAPIKeyRequest, UpdateAPIKeyRequest
from utils.crypto import encrypt, decrypt
from utils.responses import error, success, validation_error
from utils.url_guard import UnsafeURLError, ensure_public_url

bp = Blueprint("api_keys", url_prefix="/api/v1/api-keys")


def _key_preview(encrypted: str) -> str:
    """Return a masked preview of the API key."""
    try:
        raw = decrypt(encrypted)
        if len(raw) > 8:
            return raw[:4] + "..." + raw[-4:]
        return "****"
    except Exception:
        return "****"


@bp.post("/")
@require_auth
async def create_api_key(request: Request):
    try:
        body = CreateAPIKeyRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)
    for url, what in ((body.base_url, "API base URL"),):
        if url:
            try:
                await ensure_public_url(url, what=what)
            except UnsafeURLError as exc:
                return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])
    key_id = str(uuid.uuid4())

    await UserAPIKey.insert(
        UserAPIKey(
            id=key_id,
            user=user_id,
            provider=body.provider,
            label=body.label,
            key_encrypted=encrypt(body.api_key),
            base_url=body.base_url,
        )
    ).run()

    return success(
        {
            "id": key_id,
            "provider": body.provider,
            "label": body.label,
            "base_url": body.base_url,
            "is_active": True,
            "key_preview": body.api_key[:4] + "..." + body.api_key[-4:] if len(body.api_key) > 8 else "****",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        message="API key added",
        status=201,
    )


@bp.get("/")
@require_auth
async def list_api_keys(request: Request):
    user_id = str(request.ctx.user["id"])

    keys = await UserAPIKey.select().where(
        UserAPIKey.user == user_id
    ).order_by(UserAPIKey.created_at, ascending=False).run()

    result = []
    for k in keys:
        result.append({
            "id": str(k["id"]),
            "provider": k["provider"],
            "label": k["label"],
            "base_url": k["base_url"],
            "is_active": k["is_active"],
            "key_preview": _key_preview(k["key_encrypted"]),
            "created_at": str(k["created_at"]),
        })

    return success(result)


@bp.put("/<key_id:str>")
@require_auth
async def update_api_key(request: Request, key_id: str):
    try:
        body = UpdateAPIKeyRequest(**(request.json or {}))
    except Exception as exc:
        return validation_error(exc)
    for url, what in ((body.base_url, "API base URL"),):
        if url:
            try:
                await ensure_public_url(url, what=what)
            except UnsafeURLError as exc:
                return error(str(exc), status=422)

    user_id = str(request.ctx.user["id"])

    existing = await UserAPIKey.select().where(
        (UserAPIKey.id == key_id) & (UserAPIKey.user == user_id)
    ).first().run()
    if not existing:
        return error("API key not found", status=404)

    updates = body.model_dump(exclude_none=True)
    if "api_key" in updates:
        updates["key_encrypted"] = encrypt(updates.pop("api_key"))

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await UserAPIKey.update(updates).where(UserAPIKey.id == key_id).run()

    return success(message="API key updated")


@bp.delete("/<key_id:str>")
@require_auth
async def delete_api_key(request: Request, key_id: str):
    user_id = str(request.ctx.user["id"])

    existing = await UserAPIKey.select(UserAPIKey.id).where(
        (UserAPIKey.id == key_id) & (UserAPIKey.user == user_id)
    ).first().run()
    if not existing:
        return error("API key not found", status=404)

    await UserAPIKey.delete().where(UserAPIKey.id == key_id).run()
    return success(message="API key deleted")
