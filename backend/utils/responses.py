"""
Accura – Response Helpers
"""

from __future__ import annotations

from sanic import json as sanic_json
from sanic.response import HTTPResponse


def success(data=None, message: str = "OK", status: int = 200, **kwargs) -> HTTPResponse:
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    body.update(kwargs)
    return sanic_json(body, status=status)


def error(message: str = "Error", status: int = 400, errors=None, **kwargs) -> HTTPResponse:
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    body.update(kwargs)
    return sanic_json(body, status=status)


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
