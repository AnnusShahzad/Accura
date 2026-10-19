"""
Accura – Shared table base classes
"""

from __future__ import annotations

import json
from typing import Any

from piccolo.columns import JSON
from piccolo.query.methods.select import Select
from piccolo.table import Table


def _decode(value: Any) -> Any:
    if isinstance(value, (str, bytes)):
        try:
            return json.loads(value)
        except ValueError:
            return value
    # SQLite gives the column NUMERIC affinity, so a stored "7" comes
    # back as the int 7 -- already decoded.
    return value


class JSONTable(Table):
    """Table whose JSON/JSONB columns are decoded on every select.

    Piccolo returns JSON columns as raw strings unless asked otherwise,
    and its own load_json chokes on values SQLite has already coerced to
    numbers. Decode leniently in a result callback instead.
    """

    @classmethod
    def select(cls, *columns, exclude_secrets: bool = False) -> Select:
        json_names = {
            c._meta.name for c in cls._meta.columns if isinstance(c, JSON)
        }

        def decode_rows(results):
            rows = results if isinstance(results, list) else [results]
            for row in rows:
                if isinstance(row, dict):
                    for name in json_names & row.keys():
                        row[name] = _decode(row[name])
            return results

        return super().select(*columns, exclude_secrets=exclude_secrets).callback(decode_rows)
