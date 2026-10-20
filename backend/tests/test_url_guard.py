"""
Accura – SSRF guard tests (security.allow_private_urls = false)
"""

import pytest

from config import settings
from tests.conftest import register_and_login
from utils.url_guard import UnsafeURLError, ensure_public_url


@pytest.fixture
def locked_down(monkeypatch):
    monkeypatch.setitem(settings._data["security"], "allow_private_urls", False)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/admin",
    "http://localhost/x",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://0.0.0.0/",
    "file:///etc/passwd",
    "gopher://example.com/",
    "not a url",
])
async def test_private_and_odd_urls_rejected(locked_down, url):
    with pytest.raises(UnsafeURLError):
        await ensure_public_url(url)


async def test_public_literal_allowed(locked_down):
    await ensure_public_url("https://93.184.215.14/v1")


async def test_guard_is_off_by_default():
    await ensure_public_url("http://127.0.0.1:1/")


async def test_routes_reject_private_targets(locked_down, test_client, sample_user):
    headers = await register_and_login(test_client, sample_user, tier="pro")

    _, resp = await test_client.post("/api/v1/mcp-servers", json={
        "name": "internal", "url": "http://127.0.0.1:6379/",
    }, headers=headers)
    assert resp.status == 422 and "private" in resp.json["message"]

    _, resp = await test_client.post("/api/v1/api-keys", json={
        "provider": "custom", "api_key": "sk-1234567890", "base_url": "http://169.254.169.254/v1",
    }, headers=headers)
    assert resp.status == 422

    _, resp = await test_client.put("/api/v1/settings", json={
        "slack_webhook_url": "https://localhost/hook",
    }, headers=headers)
    assert resp.status == 422
