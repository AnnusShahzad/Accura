"""
Accura – Contact Routes
POST /api/v1/contact
"""

from __future__ import annotations

import uuid

from sanic import Blueprint, Request

from models.contact import ContactRequest
from schemas.admin import ContactRequest as ContactSchema
from utils.email import send_email
from utils.responses import error, success

bp = Blueprint("contact", url_prefix="/api/v1/contact")


@bp.post("/")
async def submit_contact(request: Request):
    """Public endpoint – submit a contact request (e.g. business upgrade)."""
    try:
        body = ContactSchema(**request.json)
    except Exception as exc:
        return error(str(exc), status=422)

    req_id = str(uuid.uuid4())

    await ContactRequest.insert(
        ContactRequest(
            id=req_id,
            name=body.name,
            email=body.email,
            company=body.company,
            subject=body.subject,
            message=body.message,
            request_type=body.request_type,
        )
    ).run()

    # Notify admin via email (best-effort)
    try:
        from config import settings
        admin_email = settings.get("branding.support_email", "admin@accura.ai")
        await send_email(
            to=admin_email,
            subject=f"[Contact] {body.subject or body.request_type} from {body.name}",
            text_body=f"Name: {body.name}\nEmail: {body.email}\nCompany: {body.company}\n\n{body.message}",
        )
    except Exception:
        pass  # Non-critical

    return success({"id": req_id}, message="Contact request submitted", status=201)
