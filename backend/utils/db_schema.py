"""
Accura – Database Schema Bootstrap

Creates missing tables on startup and adds columns that were introduced
after a table was first created. This keeps existing SQLite / Postgres
databases usable across upgrades without hand-written repair scripts.
"""

from __future__ import annotations

import logging

from piccolo.engine.sqlite import SQLiteEngine
from piccolo.table import Table

from models import ALL_TABLES

logger = logging.getLogger("accura.db_schema")


async def _existing_columns(table: type[Table]) -> set[str]:
    name = table._meta.tablename
    engine = table._meta.db
    if isinstance(engine, SQLiteEngine):
        rows = await table.raw(f'PRAGMA table_info("{name}")').run()
        return {r["name"] for r in rows}
    rows = await table.raw(
        "SELECT column_name FROM information_schema.columns WHERE table_name = {}",
        name,
    ).run()
    return {r["column_name"] for r in rows}


async def _add_missing_columns(table: type[Table]) -> None:
    existing = await _existing_columns(table)
    for column in table._meta.columns:
        col_name = column._meta.db_column_name
        if col_name in existing:
            continue
        ddl = column.ddl
        # SQLite cannot add UNIQUE columns in place; the unique index is
        # skipped there, which is acceptable for an upgrade path.
        if isinstance(table._meta.db, SQLiteEngine):
            ddl = ddl.replace(" UNIQUE", "")
        try:
            await table.raw(f'ALTER TABLE "{table._meta.tablename}" ADD COLUMN {ddl}').run()
            logger.info("Added missing column %s.%s", table._meta.tablename, col_name)
        except Exception as exc:
            logger.warning(
                "Could not add column %s.%s: %s", table._meta.tablename, col_name, exc
            )


async def ensure_schema() -> None:
    """Create every table if needed and back-fill newly added columns."""
    for table in ALL_TABLES:
        await table.create_table(if_not_exists=True).run()
        await _add_missing_columns(table)
    logger.info("Database schema ensured (%d tables).", len(ALL_TABLES))
