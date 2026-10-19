"""
Accura – Settings & Profile Tests
"""


async def test_get_settings(test_client, auth_headers):
    _, resp = await test_client.get("/api/v1/settings", headers=auth_headers)
    assert resp.status == 200
    data = resp.json["data"]
    assert data["global_threshold"] == 75
    assert data["max_iterations"] == 5
    assert isinstance(data["extra"], dict)


async def test_update_settings(test_client, auth_headers):
    _, resp = await test_client.put("/api/v1/settings/", json={
        "global_threshold": 85.0,
        "max_iterations": 10,
        "dark_mode": True,
        "preferred_generator_model": "deepseek-chat",
    }, headers=auth_headers)
    assert resp.status == 200

    _, resp = await test_client.get("/api/v1/settings", headers=auth_headers)
    data = resp.json["data"]
    assert float(data["global_threshold"]) == 85.0
    assert data["max_iterations"] == 10
    assert data["dark_mode"] is True
    assert data["preferred_generator_model"] == "deepseek-chat"


async def test_update_settings_rejects_out_of_range(test_client, auth_headers):
    _, resp = await test_client.put("/api/v1/settings", json={"global_threshold": 150}, headers=auth_headers)
    assert resp.status == 422
    assert resp.json["errors"][0]["field"] == "global_threshold"


async def test_update_profile(test_client, auth_headers):
    _, resp = await test_client.put("/api/v1/user/profile", json={
        "first_name": "Ada", "company": "Analytical Engines",
    }, headers=auth_headers)
    assert resp.status == 200
    assert resp.json["data"]["profile"]["first_name"] == "Ada"
    assert resp.json["data"]["user"]["email"]
