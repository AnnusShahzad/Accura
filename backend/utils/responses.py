"""
Accura – Response Helpers
"""

from __future__ import annotations

import datetime
import decimal
import json
import uuid

from sanic import json as sanic_json
from sanic.response import HTTPResponse


class _AccuraEncoder(json.JSONEncoder):
    """Custom encoder that handles common Piccolo types."""

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)


def _dumps(obj, **kwargs):
    return json.dumps(obj, cls=_AccuraEncoder, **kwargs)


def success(data=None, message: str = "OK", status: int = 200, **kwargs) -> HTTPResponse:
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    body.update(kwargs)
    return HTTPResponse(
        body=_dumps(body),
        status=status,
        content_type="application/json",
    )


def error(message: str = "Error", status: int = 400, errors=None, **kwargs) -> HTTPResponse:
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    body.update(kwargs)
    return HTTPResponse(
        body=_dumps(body),
        status=status,
        content_type="application/json",
    )


def paginated(items: list, total: int, page: int, per_page: int, **kwargs) -> HTTPResponse:
    return success(
        data={
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        },
        **kwargs,
    )


def validation_error(exc: Exception, status: int = 422) -> HTTPResponse:
    """Turn a pydantic ValidationError into a readable 422 response.

    ``str(exc)`` on a pydantic error is a multi-line dump ending in a
    documentation URL, which is useless as a toast in the frontend.
    """
    from pydantic import ValidationError as PydanticValidationError

    if isinstance(exc, PydanticValidationError):
        details = []
        for err in exc.errors():
            field = ".".join(str(p) for p in err.get("loc", ()) if p != "__root__")
            msg = str(err.get("msg", "Invalid value"))
            msg = msg.removeprefix("Value error, ")
            details.append({"field": field, "message": msg})
        message = "; ".join(
            f"{d['field']}: {d['message']}" if d["field"] else d["message"] for d in details
        )
        return error(message or "Validation error", status=status, errors=details)
    if isinstance(exc, TypeError):
        # e.g. Model(**None) or unexpected payload shape
        return error("Request body must be a JSON object", status=status)
    return error(str(exc), status=status)


def int_arg(request, name: str, default: int, *, minimum: int = 0, maximum: int | None = None) -> int:
    """Read an integer query argument, falling back to *default* when the
    value is missing or malformed instead of raising a 500."""
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value
