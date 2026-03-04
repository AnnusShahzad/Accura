"""
Accura – Settings Tests
"""

import pytest


class TestSettingsRoutes:
    """Test suite for /api/v1/settings endpoints."""

    async def _get_auth_header(self, test_client, sample_user):
        await test_client.post("/api/v1/auth/register", json=sample_user)
        _, login_resp = await test_client.post("/api/v1/auth/login", json={
            "email": sample_user["email"],
            "password": sample_user["password"],
        })
        token = login_resp.json["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_get_settings(self, test_client, sample_user):
        headers = await self._get_auth_header(test_client, sample_user)
        _, response = await test_client.get("/api/v1/settings/", headers=headers)
        assert response.status == 200
        data = response.json["data"]
        assert "global_threshold" in data
        assert "max_iterations" in data

    @pytest.mark.asyncio
    async def test_update_settings(self, test_client, sample_user):
        headers = await self._get_auth_header(test_client, sample_user)
        _, response = await test_client.put("/api/v1/settings/", json={
            "global_threshold": 85.0,
            "max_iterations": 10,
            "dark_mode": True,
            "preferred_generator_model": "deepseek-3",
        }, headers=headers)
        assert response.status == 200

        _, get_resp = await test_client.get("/api/v1/settings/", headers=headers)
        data = get_resp.json["data"]
        assert float(data["global_threshold"]) == 85.0
        assert data["max_iterations"] == 10
        assert data["dark_mode"] is True
