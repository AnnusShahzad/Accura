"""
Accura Backend – Piccolo ORM Configuration
"""

from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

from config import settings

DB = PostgresEngine(
    config={
        "host": settings.get("database.host", "localhost"),
        "port": settings.get("database.port", 5432),
        "database": settings.get("database.name", "accura"),
        "user": settings.get("database.user", "accura"),
        "password": settings.get("database.password", "changeme"),
    },
    extensions=("uuid-ossp",),
)

APP_REGISTRY = AppRegistry(
    apps=[
        "piccolo_app",
        "piccolo.apps.user.piccolo_app",
        "piccolo_admin.piccolo_app",
    ]
)
