"""
Smoke-test a running Accura backend over HTTP.

    python scripts/create_admin.py smoke@example.com --password 'Sm0ke!Test1'
    python scripts/smoke_test.py --email smoke@example.com --password 'Sm0ke!Test1'

Needs an existing, verified account (registration requires the emailed
OTP). Does not call any AI provider: the conversation it creates is
deleted straight away.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

PASS = 0
FAIL = 0


def api(base, method, path, token=None, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    if token:
        hdrs["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw}
    except urllib.error.URLError as e:
        return 0, {"error": str(e)}


def check(name, status, expected):
    global PASS, FAIL
    ok = status == expected
    PASS, FAIL = PASS + ok, FAIL + (not ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {status} (expected {expected})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="http://localhost:8000/api/v1")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    base = args.base.rstrip("/")

    s, r = api(base, "GET", "/health")
    check("GET /health", s, 200)
    if s == 0:
        sys.exit(f"Backend not reachable at {base}: {r.get('error')}")

    s, r = api(base, "POST", "/auth/login", body={"email": args.email, "password": args.password})
    check("POST /auth/login", s, 200)
    if s != 200:
        sys.exit(f"Login failed: {r.get('message')}")
    tk = r["data"]["access_token"]

    s, _ = api(base, "OPTIONS", "/chat", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    check("CORS preflight /chat", s, 204)

    for path in ["/user/me", "/settings", "/notifications", "/notifications/unread-count",
                 "/billing/subscription", "/billing/tokens", "/billing/transactions",
                 "/api-keys", "/mcp-servers", "/chat"]:
        s, _ = api(base, "GET", path, token=tk)
        check(f"GET {path}", s, 200)

    s, _ = api(base, "GET", "/billing/plans")
    check("GET /billing/plans (public)", s, 200)

    s, _ = api(base, "PUT", "/user/profile", token=tk, body={"company": "Smoke Test"})
    check("PUT /user/profile", s, 200)

    s, _ = api(base, "PUT", "/settings", token=tk, body={"notify_in_app": True})
    check("PUT /settings", s, 200)

    s, r = api(base, "POST", "/chat", token=tk, body={"title": "Smoke test", "prompt": "ping"})
    check("POST /chat", s, 201)
    if s == 201:
        cid = r["data"]["id"]
        s, _ = api(base, "GET", f"/chat/{cid}", token=tk)
        check("GET /chat/:id", s, 200)
        s, _ = api(base, "PATCH", f"/chat/{cid}/rename", token=tk, body={"title": "Renamed"})
        check("PATCH /chat/:id/rename", s, 200)
        s, _ = api(base, "DELETE", f"/chat/{cid}", token=tk)
        check("DELETE /chat/:id", s, 200)

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
