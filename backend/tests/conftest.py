"""
Accura – Test Configuration & Fixtures

Tests run against a throwaway SQLite database and never touch the
developer's real database, SMTP server or AI providers.
"""

import os
import tempfile
import uuid

from cryptography.fernet import Fernet

# Configure the environment *before* anything imports config.py.
# Defaults to a throwaway SQLite file; set TEST_DB_ENGINE=postgres (plus
# DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD) to run against Postgres.
# The Postgres database is wiped at the start of the run.
_TMP_DIR = tempfile.mkdtemp(prefix="accura-tests-")
TEST_DB_ENGINE = os.environ.get("TEST_DB_ENGINE", "sqlite")
os.environ["DB_ENGINE"] = TEST_DB_ENGINE
os.environ["DB_SQLITE_PATH"] = os.path.join(_TMP_DIR, "test.db")
os.environ["APP_DEBUG"] = "false"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["SMTP_HOST"] = "127.0.0.1"
os.environ["SMTP_PORT"] = "1"  # nothing listens here; sends fail fast
os.environ["REDIS_URL"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["STRIPE_SECRET_KEY"] = ""

import pytest  # noqa: E402
from sanic_testing import TestManager  # noqa: E402

from app import app as accura_app  # noqa: E402
from models.user import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
async def _fresh_postgres():
    if TEST_DB_ENGINE == "postgres":
        from models import ALL_TABLES

        for table in reversed(ALL_TABLES):
            await table.raw(f'DROP TABLE IF EXISTS "{table._meta.tablename}" CASCADE').run()
    yield


@pytest.fixture(scope="session")
def sanic_app():
    TestManager(accura_app)
    accura_app.ctx.keep_db_pool = True
    return accura_app


@pytest.fixture(scope="session")
def test_client(sanic_app):
    return sanic_app.asgi_client


@pytest.fixture
def sample_user():
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{suffix}@example.com",
        "username": f"testuser_{suffix}",
        "password": "SecureP@ss123",
        "first_name": "Test",
        "last_name": "User",
    }


async def register_and_login(client, user: dict, *, admin: bool = False, tier: str | None = None) -> dict:
    """Register *user*, mark it verified (skipping the OTP email), log in
    and return an Authorization header."""
    _, resp = await client.post("/api/v1/auth/register", json=user)
    assert resp.status in (200, 201), resp.json
    updates = {User.is_verified: True}
    if admin:
        updates[User.is_admin] = True
    if tier:
        updates[User.tier] = tier
    await User.update(updates).where(User.email == user["email"]).run()

    _, resp = await client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert resp.status == 200, resp.json
    return {"Authorization": f"Bearer {resp.json['data']['access_token']}"}


@pytest.fixture
async def auth_headers(test_client, sample_user):
    return await register_and_login(test_client, sample_user)


@pytest.fixture
async def admin_headers(test_client):
    suffix = uuid.uuid4().hex[:8]
    user = {
        "email": f"admin_{suffix}@example.com",
        "username": f"admin_{suffix}",
        "password": "SecureP@ss123",
    }
    return await register_and_login(test_client, user, admin=True)
