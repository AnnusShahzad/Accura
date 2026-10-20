"""
Accura – Authentication Tests
"""

from models.user import User
from services.auth_service import _password_fingerprint, create_access_token
from tests.conftest import register_and_login


async def _register(client, user):
    _, resp = await client.post("/api/v1/auth/register", json=user)
    return resp


async def _mark_verified(email):
    await User.update({User.is_verified: True}).where(User.email == email).run()


async def test_register_success(test_client, sample_user):
    resp = await _register(test_client, sample_user)
    assert resp.status == 201
    assert resp.json["success"] is True
    assert resp.json["data"]["email"] == sample_user["email"]


async def test_register_rejects_weak_password(test_client, sample_user):
    sample_user["password"] = "password"
    resp = await _register(test_client, sample_user)
    assert resp.status == 422
    # Errors are flattened into a readable message, not a pydantic dump
    assert "errors.pydantic.dev" not in resp.json["message"]
    assert resp.json["errors"][0]["field"] == "password"


async def test_register_duplicate_unverified_resends_code(test_client, sample_user):
    await _register(test_client, sample_user)
    resp = await _register(test_client, sample_user)
    assert resp.status == 200
    assert resp.json["data"]["already_exists_unverified"] is True


async def test_register_duplicate_verified_email(test_client, sample_user):
    await _register(test_client, sample_user)
    await _mark_verified(sample_user["email"])
    resp = await _register(test_client, sample_user)
    assert resp.status == 422


async def test_login_requires_verification(test_client, sample_user):
    await _register(test_client, sample_user)
    _, resp = await test_client.post("/api/v1/auth/login", json={
        "email": sample_user["email"], "password": sample_user["password"],
    })
    assert resp.status == 403
    assert "verify your email" in resp.json["message"].lower()


async def test_verify_otp_then_login(test_client, sample_user):
    await _register(test_client, sample_user)
    user = await User.select(User.otp_code).where(User.email == sample_user["email"]).first().run()
    _, resp = await test_client.post("/api/v1/auth/verify-otp", json={
        "email": sample_user["email"], "otp": user["otp_code"],
    })
    assert resp.status == 200
    _, resp = await test_client.post("/api/v1/auth/login", json={
        "email": sample_user["email"], "password": sample_user["password"],
    })
    assert resp.status == 200
    assert "access_token" in resp.json["data"]
    assert "refresh_token" in resp.json["data"]


async def test_login_wrong_password(test_client, sample_user):
    await _register(test_client, sample_user)
    await _mark_verified(sample_user["email"])
    _, resp = await test_client.post("/api/v1/auth/login", json={
        "email": sample_user["email"], "password": "WrongPassword1!",
    })
    assert resp.status == 401


async def test_protected_route_no_token(test_client):
    _, resp = await test_client.get("/api/v1/user/me")
    assert resp.status == 401


async def test_protected_route_with_token(test_client, sample_user):
    headers = await register_and_login(test_client, sample_user)
    _, resp = await test_client.get("/api/v1/user/me", headers=headers)
    assert resp.status == 200
    assert resp.json["data"]["user"]["email"] == sample_user["email"]


async def test_refresh_token(test_client, sample_user):
    await _register(test_client, sample_user)
    await _mark_verified(sample_user["email"])
    _, login = await test_client.post("/api/v1/auth/login", json={
        "email": sample_user["email"], "password": sample_user["password"],
    })
    refresh = login.json["data"]["refresh_token"]

    _, resp = await test_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status == 200
    assert "access_token" in resp.json["data"]

    # A refresh token must not be accepted as an access token
    _, resp = await test_client.get(
        "/api/v1/user/me", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert resp.status == 401


async def test_reset_password_link_is_single_use(test_client, sample_user):
    await _register(test_client, sample_user)
    await _mark_verified(sample_user["email"])
    user = await User.select().where(User.email == sample_user["email"]).first().run()
    token = create_access_token(
        str(user["id"]),
        extra={"type": "password_reset", "pwd": _password_fingerprint(user["hashed_password"])},
    )

    # Reset tokens can't be used to call the API
    _, resp = await test_client.get("/api/v1/user/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 401

    _, resp = await test_client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "weak",
    })
    assert resp.status == 422

    _, resp = await test_client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "N3w!Password",
    })
    assert resp.status == 200

    _, resp = await test_client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "An0ther!Pass",
    })
    assert resp.status == 401

    _, resp = await test_client.post("/api/v1/auth/login", json={
        "email": sample_user["email"], "password": "N3w!Password",
    })
    assert resp.status == 200


async def test_forgot_password_does_not_leak_accounts(test_client):
    _, resp = await test_client.post("/api/v1/auth/forgot-password", json={
        "email": "nobody@example.com",
    })
    assert resp.status == 200


async def test_email_change_confirmation(test_client, sample_user):
    headers = await register_and_login(test_client, sample_user)
    user = await User.select().where(User.email == sample_user["email"]).first().run()
    token = create_access_token(
        str(user["id"]), extra={"type": "email_change", "new_email": "changed_" + sample_user["email"]}
    )
    # The public endpoint works with a trailing slash too
    _, resp = await test_client.post("/api/v1/auth/verify-email-change/", json={"token": token})
    assert resp.status == 200
    _, resp = await test_client.get("/api/v1/user/me", headers=headers)
    assert resp.json["data"]["user"]["email"] == "changed_" + sample_user["email"]


async def test_check_username(test_client, sample_user):
    _, resp = await test_client.get(f"/api/v1/auth/check-username/{sample_user['username']}")
    assert resp.status == 200
    assert resp.json["data"]["available"] is True


async def test_health_check(test_client):
    _, resp = await test_client.get("/api/v1/health")
    assert resp.status == 200
    assert resp.json["status"] == "healthy"
