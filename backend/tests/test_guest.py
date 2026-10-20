"""
Accura – Guest accounts, closed registration, bootstrap admin and the
maintenance jobs that clean up after them.
"""

from datetime import datetime, timedelta, timezone

import pytest

import routes.auth as auth_routes
from config import settings
from models.chat import ChatMessage, Conversation
from models.user import User
from services.auth_service import ensure_bootstrap_admin
from services.maintenance import (
    fail_interrupted_runs,
    purge_expired_guests,
    purge_temporary_conversations,
)
from tests.fakes import FakeAI
from tests.test_chat import _wait_done


@pytest.fixture
def guests_on(monkeypatch):
    monkeypatch.setitem(settings._data["auth"]["guest"], "enabled", True)
    auth_routes._guest_signins.clear()
    auth_routes._all_guest_signins.clear()


async def _guest(client, ip="203.0.113.7"):
    _, resp = await client.post("/api/v1/auth/guest", headers={"X-Forwarded-For": ip})
    return resp


async def test_public_config(test_client, guests_on, monkeypatch):
    monkeypatch.setitem(settings._data["auth"], "registration_enabled", False)
    _, resp = await test_client.get("/api/v1/public/config")
    data = resp.json["data"]
    assert data["registration_enabled"] is False
    assert data["guest"]["enabled"] is True
    assert data["billing_mode"] == "demo"
    assert "default_generator_model" in data["ai"]


async def test_guest_disabled_by_default(test_client):
    auth_routes._guest_signins.clear()
    resp = await _guest(test_client)
    assert resp.status == 403


async def test_guest_session_and_restrictions(test_client, guests_on, monkeypatch):
    resp = await _guest(test_client)
    assert resp.status == 201
    headers = {"Authorization": f"Bearer {resp.json['data']['access_token']}"}

    _, me = await test_client.get("/api/v1/user/me", headers=headers)
    user = me.json["data"]["user"]
    assert user["is_guest"] is True and user["expires_at"]

    _, r = await test_client.post("/api/v1/auth/change-password", json={
        "old_password": "x", "new_password": "N3w!Password",
    }, headers=headers)
    assert r.status == 403
    _, r = await test_client.post("/api/v1/auth/request-email-change", json={"email": "a@example.com"},
                                  headers=headers)
    assert r.status == 403
    _, r = await test_client.post("/api/v1/billing/subscribe", json={"plan_name": "pro"}, headers=headers)
    assert r.status == 403

    # Iterations are capped even if the guest asks for more
    FakeAI(scores=(10,)).install(monkeypatch)
    _, r = await test_client.post("/api/v1/chat", json={
        "prompt": "hi", "threshold": 99, "max_iterations": 20,
    }, headers=headers)
    conv = await _wait_done(test_client, r.json["data"]["id"], headers)
    assert len(conv["iterations"]) == settings.get("auth.guest.max_iterations")


async def test_guest_signins_are_throttled_per_ip(test_client, guests_on):
    for _ in range(5):
        assert (await _guest(test_client, ip="198.51.100.1")).status == 201
    assert (await _guest(test_client, ip="198.51.100.1")).status == 429
    assert (await _guest(test_client, ip="198.51.100.2")).status == 201


async def test_expired_guests_are_locked_out_and_purged(test_client, guests_on, monkeypatch):
    resp = await _guest(test_client)
    tokens = resp.json["data"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    FakeAI().install(monkeypatch)
    _, r = await test_client.post("/api/v1/chat", json={"prompt": "hi"}, headers=headers)
    conv_id = r.json["data"]["id"]
    await _wait_done(test_client, conv_id, headers)

    _, me = await test_client.get("/api/v1/user/me", headers=headers)
    user_id = me.json["data"]["user"]["id"]
    await User.update({User.expires_at: datetime.now(timezone.utc) - timedelta(minutes=1)}).where(
        User.id == user_id
    ).run()

    _, r = await test_client.get("/api/v1/user/me", headers=headers)
    assert r.status == 401
    _, r = await test_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status == 401

    assert await purge_expired_guests() >= 1
    assert not await User.exists().where(User.id == user_id).run()
    assert not await Conversation.exists().where(Conversation.id == conv_id).run()
    assert not await ChatMessage.exists().where(ChatMessage.conversation == conv_id).run()


async def test_registration_can_be_closed(test_client, sample_user, monkeypatch):
    monkeypatch.setitem(settings._data["auth"], "registration_enabled", False)
    _, resp = await test_client.post("/api/v1/auth/register", json=sample_user)
    assert resp.status == 403
    assert "Registration is closed" in resp.json["message"]


async def test_bootstrap_admin_creates_promotes_and_resets(monkeypatch):
    boot = settings._data["auth"]["bootstrap_admin"]
    monkeypatch.setitem(boot, "email", "Boot@Example.com")
    monkeypatch.setitem(boot, "password", "B00t!Strap")
    await ensure_bootstrap_admin()
    user = await User.select().where(User.email == "boot@example.com").first().run()
    assert user["is_admin"] and user["is_verified"]

    await User.update({User.is_admin: False}).where(User.id == user["id"]).run()
    monkeypatch.setitem(boot, "password", "N3w!Strap99")
    await ensure_bootstrap_admin()
    again = await User.select().where(User.id == user["id"]).first().run()
    assert again["is_admin"] and again["hashed_password"] != user["hashed_password"]

    monkeypatch.setitem(boot, "password", "weak")  # rejected, nothing changes
    await ensure_bootstrap_admin()


async def test_interrupted_and_temporary_cleanup(test_client, auth_headers, monkeypatch):
    FakeAI().install(monkeypatch)
    _, r = await test_client.post("/api/v1/chat", json={"prompt": "temp", "is_temporary": True},
                                  headers=auth_headers)
    temp_id = r.json["data"]["id"]
    await _wait_done(test_client, temp_id, auth_headers)

    # A run that stopped making progress long ago
    _, r = await test_client.post("/api/v1/chat", json={"prompt": "stuck"}, headers=auth_headers)
    stuck_id = r.json["data"]["id"]
    await _wait_done(test_client, stuck_id, auth_headers)
    long_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    await Conversation.update({Conversation.status: "active", Conversation.updated_at: long_ago}).where(
        Conversation.id == stuck_id
    ).run()
    assert await fail_interrupted_runs() >= 1
    _, r = await test_client.get(f"/api/v1/chat/{stuck_id}", headers=auth_headers)
    assert r.json["data"]["status"] == "failed"
    assert r.json["data"]["messages"][-1]["metadata"]["type"] == "error"

    await Conversation.update({Conversation.created_at: datetime.now(timezone.utc) - timedelta(days=2)}).where(
        Conversation.id == temp_id
    ).run()
    assert await purge_temporary_conversations() >= 1
    _, r = await test_client.get(f"/api/v1/chat/{temp_id}", headers=auth_headers)
    assert r.status == 404


async def test_site_wide_guest_cap_ignores_forged_ips(test_client, guests_on, monkeypatch):
    monkeypatch.setitem(settings._data["auth"]["guest"], "signups_per_hour", 3)
    statuses = [(await _guest(test_client, ip=f"203.0.113.{i}")).status for i in range(5)]
    assert statuses == [201, 201, 201, 429, 429]
