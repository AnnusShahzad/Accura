"""
Accura – Chat / Conversation Tests
"""

import pytest


class TestChatRoutes:
    """Test suite for /api/v1/chat/* endpoints."""

    async def _get_auth_header(self, test_client, sample_user):
        await test_client.post("/api/v1/auth/register", json=sample_user)
        _, login_resp = await test_client.post("/api/v1/auth/login", json={
            "email": sample_user["email"],
            "password": sample_user["password"],
        })
        token = login_resp.json["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_create_conversation(self, test_client, sample_user):
        headers = await self._get_auth_header(test_client, sample_user)
        _, response = await test_client.post("/api/v1/chat/", json={
            "prompt": "Explain quantum computing in simple terms",
            "generator_model": "gpt-5.2",
            "generator_provider": "openai",
        }, headers=headers)
        assert response.status == 201
        assert response.json["success"] is True

    @pytest.mark.asyncio
    async def test_list_conversations(self, test_client, sample_user):
        headers = await self._get_auth_header(test_client, sample_user)
        _, response = await test_client.get("/api/v1/chat/", headers=headers)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_rename_conversation(self, test_client, sample_user):
        headers = await self._get_auth_header(test_client, sample_user)
        _, create_resp = await test_client.post("/api/v1/chat/", json={
            "prompt": "Test prompt",
            "generator_model": "gpt-5.2",
            "generator_provider": "openai",
        }, headers=headers)
        conv_id = create_resp.json["data"]["id"]

        _, rename_resp = await test_client.patch(
            f"/api/v1/chat/{conv_id}/rename",
            json={"title": "Renamed Conversation"},
            headers=headers,
        )
        assert rename_resp.status == 200
