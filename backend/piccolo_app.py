"""
Accura – Piccolo App Definition
"""

import os

from piccolo.conf.apps import AppConfig

from models import ALL_TABLES

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="accura",
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "migrations"),
    table_classes=list(ALL_TABLES),
)
