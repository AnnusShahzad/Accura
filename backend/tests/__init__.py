"""
Accura – Test Configuration & Fixtures
"""

import asyncio
import os
import uuid

import pytest
from sanic_testing import TestManager

# Override DB to use test database before any imports
os.environ["DB_NAME"] = "accura_test"
os.environ["APP_DEBUG"] = "true"
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcw==___="  # placeholder

from app import create_app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def sanic_app():
    app = create_app()
    TestManager(app)
    return app


@pytest.fixture
def test_client(sanic_app):
    return sanic_app.asgi_client


@pytest.fixture
def sample_user():
    return {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "password": "SecureP@ss123",
        "first_name": "Test",
        "last_name": "User",
    }
