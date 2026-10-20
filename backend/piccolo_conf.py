"""
Accura Backend – Piccolo ORM Configuration

The engine is chosen from ``database.engine`` (env: DB_ENGINE):
  * sqlite   – zero-setup local development (default)
  * postgres – Docker / production deployments

A ``DATABASE_URL`` (postgres://user:pass@host:port/db, as provided by
Render, Neon, Supabase, Railway, ...) implies postgres and takes
precedence over the individual DB_* settings. ``?sslmode=require`` in the
URL is honoured.
"""

import os

from piccolo.conf.apps import AppRegistry

from config import settings

_url = str(settings.get("database.url", "") or "")
_engine = "postgres" if _url else str(settings.get("database.engine", "sqlite")).lower()

if _engine in ("postgres", "postgresql"):
    from piccolo.engine.postgres import PostgresEngine

    if _url:
        # asyncpg understands postgres:// and postgresql:// DSNs directly
        _config = {"dsn": _url}
    else:
        _config = {
            "host": settings.get("database.host", "localhost"),
            "port": int(settings.get("database.port", 5432)),
            "database": settings.get("database.name", "accura"),
            "user": settings.get("database.user", "accura"),
            "password": settings.get("database.password", ""),
        }
    DB = PostgresEngine(config=_config, extensions=())
elif _engine == "sqlite":
    from piccolo.engine.sqlite import SQLiteEngine

    _path = settings.get("database.sqlite_path", "accura_dev.db")
    if not os.path.isabs(_path):
        _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _path)
    DB = SQLiteEngine(path=_path)
else:
    raise RuntimeError(f"Unsupported database.engine '{_engine}' (use sqlite or postgres)")

APP_REGISTRY = AppRegistry(apps=["piccolo_app"])
