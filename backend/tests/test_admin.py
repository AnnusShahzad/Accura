"""
Accura – Admin API Tests
"""

from config import settings


async def test_admin_routes_require_admin(test_client, auth_headers):
    _, resp = await test_client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert resp.status == 403


async def test_dashboard(test_client, admin_headers):
    _, resp = await test_client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert resp.status == 200
    data = resp.json["data"]
    assert {"total_users", "tokens_generated_month", "tier_distribution"} <= set(data)


async def test_user_search_counts_matches(test_client, admin_headers, sample_user, auth_headers):
    term = sample_user["username"].upper()  # search is case-insensitive
    _, resp = await test_client.get(f"/api/v1/admin/users?search={term}", headers=admin_headers)
    assert resp.status == 200
    assert resp.json["data"]["total"] == 1
    user_id = resp.json["data"]["items"][0]["id"]

    _, resp = await test_client.put(f"/api/v1/admin/users/{user_id}", json={"tier": "pro"},
                                    headers=admin_headers)
    assert resp.status == 200
    assert resp.json["data"]["tier"] == "pro"
    assert "hashed_password" not in resp.json["data"]


async def test_admin_cannot_demote_self(test_client, admin_headers):
    _, me = await test_client.get("/api/v1/user/me", headers=admin_headers)
    my_id = me.json["data"]["user"]["id"]
    _, resp = await test_client.put(f"/api/v1/admin/users/{my_id}", json={"is_admin": False},
                                    headers=admin_headers)
    assert resp.status == 400


async def test_config_overrides_apply_at_runtime(test_client, admin_headers):
    _, resp = await test_client.put("/api/v1/admin/config", json={
        "key": "evaluation.default_max_iterations", "value": 7, "description": "test",
    }, headers=admin_headers)
    assert resp.status == 200
    assert settings.get("evaluation.default_max_iterations") == 7

    _, resp = await test_client.put("/api/v1/admin/config", json={
        "key": "branding.company_name", "value": "Acme",
    }, headers=admin_headers)
    _, resp = await test_client.get("/api/v1/admin/config", headers=admin_headers)
    values = {c["key"]: c["value"] for c in resp.json["data"]}
    assert values["branding.company_name"] == "Acme"  # a string, not '"Acme"'

    for key in ("evaluation.default_max_iterations", "branding.company_name"):
        _, resp = await test_client.delete(f"/api/v1/admin/config/{key}", headers=admin_headers)
        assert resp.status == 200
    assert settings.get("evaluation.default_max_iterations") == 5


async def test_plans_update_features(test_client, admin_headers):
    _, resp = await test_client.get("/api/v1/admin/plans", headers=admin_headers)
    pro = [p for p in resp.json["data"] if p["name"] == "pro"][0]
    _, resp = await test_client.put(f"/api/v1/admin/plans/{pro['id']}", json={
        "features": ["One", "Two"], "requests_per_minute": 61,
    }, headers=admin_headers)
    assert resp.status == 200
    assert resp.json["data"]["features"] == ["One", "Two"]
    assert resp.json["data"]["requests_per_minute"] == 61


async def test_domain_rules_normalized(test_client, admin_headers):
    _, resp = await test_client.post("/api/v1/admin/domain-rules", json={
        "domain": "https://www.Example.org/path", "rule_type": "blacklist",
    }, headers=admin_headers)
    assert resp.status == 201
    assert resp.json["data"]["domain"] == "example.org"
    _, resp = await test_client.post("/api/v1/admin/domain-rules", json={
        "domain": "example.org", "rule_type": "blacklist",
    }, headers=admin_headers)
    assert resp.status == 409


async def test_global_mcp_crud(test_client, admin_headers, auth_headers):
    _, resp = await test_client.post("/api/v1/admin/mcp-servers", json={
        "name": "Global", "url": "https://mcp.example.com/mcp",
    }, headers=admin_headers)
    assert resp.status == 201
    server_id = resp.json["data"]["id"]

    # Users see global servers in their own list
    _, resp = await test_client.get("/api/v1/mcp-servers", headers=auth_headers)
    assert any(s["id"] == server_id and s["is_global"] for s in resp.json["data"])

    _, resp = await test_client.put(f"/api/v1/admin/mcp-servers/{server_id}",
                                    json={"bogus_column": 1, "is_active": False}, headers=admin_headers)
    assert resp.status == 200
    assert resp.json["data"]["is_active"] is False

    _, resp = await test_client.delete(f"/api/v1/admin/mcp-servers/{server_id}", headers=admin_headers)
    assert resp.status == 200


async def test_contact_flow(test_client, admin_headers):
    _, resp = await test_client.post("/api/v1/contact", json={
        "name": "Tester", "email": "not-an-email", "message": "Hello",
    })
    assert resp.status == 422
    _, resp = await test_client.post("/api/v1/contact/", json={
        "name": "Tester", "email": "t@example.com", "message": "Hello", "request_type": "business_upgrade",
    })
    assert resp.status == 201
    req_id = resp.json["data"]["id"]

    _, resp = await test_client.put(f"/api/v1/admin/contact-requests/{req_id}",
                                    json={"status": "resolved"}, headers=admin_headers)
    assert resp.status == 200
    _, resp = await test_client.put(f"/api/v1/admin/contact-requests/{req_id}",
                                    json={"status": "open"}, headers=admin_headers)
    assert resp.json["data"]["is_resolved"] is False
