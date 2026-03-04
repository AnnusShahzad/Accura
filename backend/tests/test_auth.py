"""
Accura – Authentication Tests
"""

import pytest


class TestAuthRoutes:
    """Test suite for /api/v1/auth/* endpoints."""

    @pytest.mark.asyncio
    async def test_register_success(self, test_client, sample_user):
        _, response = await test_client.post("/api/v1/auth/register", json=sample_user)
        assert response.status == 201
        data = response.json
        assert data["success"] is True
        assert "id" in data["data"]
        assert data["data"]["email"] == sample_user["email"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_client, sample_user):
        # First registration
        await test_client.post("/api/v1/auth/register", json=sample_user)
        # Duplicate
        _, response = await test_client.post("/api/v1/auth/register", json=sample_user)
        assert response.status == 422

    @pytest.mark.asyncio
    async def test_login_success(self, test_client, sample_user):
        # Register first
        await test_client.post("/api/v1/auth/register", json=sample_user)
        # Login
        _, response = await test_client.post("/api/v1/auth/login", json={
            "email": sample_user["email"],
            "password": sample_user["password"],
        })
        assert response.status == 200
        data = response.json
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client, sample_user):
        await test_client.post("/api/v1/auth/register", json=sample_user)
        _, response = await test_client.post("/api/v1/auth/login", json={
            "email": sample_user["email"],
            "password": "WrongPassword123",
        })
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_protected_route_no_token(self, test_client):
        _, response = await test_client.get("/api/v1/user/me")
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_token(self, test_client, sample_user):
        await test_client.post("/api/v1/auth/register", json=sample_user)
        _, login_resp = await test_client.post("/api/v1/auth/login", json={
            "email": sample_user["email"],
            "password": sample_user["password"],
        })
        token = login_resp.json["data"]["access_token"]

        _, response = await test_client.get(
            "/api/v1/user/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status == 200
        assert response.json["data"]["email"] == sample_user["email"]

    @pytest.mark.asyncio
    async def test_refresh_token(self, test_client, sample_user):
        await test_client.post("/api/v1/auth/register", json=sample_user)
        _, login_resp = await test_client.post("/api/v1/auth/login", json={
            "email": sample_user["email"],
            "password": sample_user["password"],
        })
        refresh = login_resp.json["data"]["refresh_token"]

        _, response = await test_client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        })
        assert response.status == 200
        assert "access_token" in response.json["data"]

    @pytest.mark.asyncio
    async def test_health_check(self, test_client):
        _, response = await test_client.get("/api/v1/health")
        assert response.status == 200
        assert response.json["status"] == "healthy"
