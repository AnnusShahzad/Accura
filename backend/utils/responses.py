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
