"""
Accura – Billing Tests (demo mode + Stripe webhook verification)
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

from config import settings
from models.subscription import Subscription, Transaction
from services.billing_service import renew_due_subscriptions


async def test_plans_are_public_and_decoded(test_client):
    _, resp = await test_client.get("/api/v1/billing/plans")
    assert resp.status == 200
    names = [p["name"] for p in resp.json["data"]]
    assert names == ["basic", "pro", "business"]
    assert isinstance(resp.json["data"][1]["features"], list)


async def test_free_user_subscription_shape(test_client, auth_headers):
    _, resp = await test_client.get("/api/v1/billing/subscription", headers=auth_headers)
    data = resp.json["data"]
    assert data["plan_name"] == "basic"
    assert data["billing_mode"] == "demo"


async def test_demo_upgrade_cancel_cycle(test_client, auth_headers):
    _, resp = await test_client.post("/api/v1/billing/subscribe", json={
        "plan_name": "pro", "billing_cycle": "yearly",
    }, headers=auth_headers)
    assert resp.status == 201, resp.json
    assert resp.json["data"]["plan_name"] == "pro"
    assert resp.json["data"]["current_period_end"]

    _, me = await test_client.get("/api/v1/user/me", headers=auth_headers)
    assert me.json["data"]["user"]["tier"] == "pro"

    _, txns = await test_client.get("/api/v1/billing/transactions", headers=auth_headers)
    assert len(txns.json["data"]) == 1
    assert txns.json["data"][0]["amount"] == 299.99

    # Choosing Basic again downgrades
    _, resp = await test_client.post("/api/v1/billing/subscribe", json={"plan_name": "basic"},
                                     headers=auth_headers)
    assert resp.status == 200
    _, me = await test_client.get("/api/v1/user/me", headers=auth_headers)
    assert me.json["data"]["user"]["tier"] == "basic"

    _, resp = await test_client.post("/api/v1/billing/cancel", headers=auth_headers)
    assert resp.status == 404


async def test_business_requires_contact(test_client, auth_headers):
    _, resp = await test_client.post("/api/v1/billing/subscribe", json={"plan_name": "business"},
                                     headers=auth_headers)
    assert resp.status == 403
    _, resp = await test_client.post("/api/v1/billing/subscribe", json={"plan_name": "gold"},
                                     headers=auth_headers)
    assert resp.status == 422


async def test_demo_subscriptions_renew(test_client, auth_headers):
    _, resp = await test_client.post("/api/v1/billing/subscribe", json={"plan_name": "pro"},
                                     headers=auth_headers)
    sub_id = resp.json["data"]["id"]
    past = datetime.now(timezone.utc) - timedelta(days=1)
    await Subscription.update({Subscription.current_period_end: past}).where(
        Subscription.id == sub_id
    ).run()

    assert await renew_due_subscriptions() >= 1
    sub = await Subscription.select().where(Subscription.id == sub_id).first().run()
    end = sub["current_period_end"]
    end = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
    assert end > datetime.now(timezone.utc)
    assert await Transaction.count().where(Transaction.subscription == sub_id).run() == 2


async def test_token_usage(test_client, auth_headers):
    _, resp = await test_client.get("/api/v1/billing/tokens", headers=auth_headers)
    assert resp.status == 200
    assert resp.json["data"]["breakdown"] == []


async def test_stripe_webhook_signature(test_client, monkeypatch):
    _, resp = await test_client.post("/api/v1/billing/webhook", data="{}")
    assert resp.status == 503  # not configured

    secret = "whsec_test"
    monkeypatch.setitem(settings._data.setdefault("billing", {}), "stripe_webhook_secret", secret)
    payload = json.dumps({"id": "evt_1", "type": "ping", "data": {"object": {}}})
    ts = int(time.time())
    good = hmac.new(secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()

    _, resp = await test_client.post("/api/v1/billing/webhook", data=payload,
                                     headers={"Stripe-Signature": f"t={ts},v1=deadbeef"})
    assert resp.status == 400
    _, resp = await test_client.post("/api/v1/billing/webhook", data=payload,
                                     headers={"Stripe-Signature": f"t={ts},v1={good}"})
    assert resp.status == 200
