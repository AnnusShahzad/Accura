"""
Accura Backend – Piccolo ORM Configuration
"""

import os

from piccolo.conf.apps import AppRegistry
from piccolo.engine.sqlite import SQLiteEngine

DB = SQLiteEngine(
    path=os.path.join(os.path.dirname(__file__), "accura_dev.db"),
)

APP_REGISTRY = AppRegistry(
    apps=[
        "piccolo_app",
        "piccolo.apps.user.piccolo_app",
        "piccolo_admin.piccolo_app",
    ]
)
