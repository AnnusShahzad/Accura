"""End-to-end API test script."""
import urllib.request
import json
import sys
import time

BASE = "http://localhost:8000/api/v1"
PASS = 0
FAIL = 0
DELAY = 0.15  # small delay between requests to avoid overwhelming single-worker server

def api(method, path, token=None, body=None, retries=2):
    time.sleep(DELAY)
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    for attempt in range(retries + 1):
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req)
            return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())
        except (ConnectionRefusedError, ConnectionResetError, urllib.error.URLError) as e:
            if attempt < retries:
                print(f"    [RETRY] {method} {path} attempt {attempt+1} failed, retrying...")
                time.sleep(1)
            else:
                return 0, {"error": str(e)}

def check(name, status, expected, detail=""):
    global PASS, FAIL
    ok = status == expected
    symbol = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    extra = f" - {detail}" if detail else ""
    print(f"  [{symbol}] {name}: {status} (expected {expected}){extra}")

# ── Register & Login ──
_, reg = api("POST", "/auth/register", body={"email":"e2e@test.dev","username":"e2euser","password":"E2ePass99"})
print("Register:", reg.get("message"))

_, lr = api("POST", "/auth/login", body={"email":"e2e@test.dev","password":"E2ePass99"})
tk = lr["data"]["access_token"]
check("Login", 200, 200)

# ── CORS Preflight ──
for path in ["/user/me", "/chat", "/settings", "/notifications", "/admin/dashboard", "/mcp-servers"]:
    time.sleep(DELAY)
    req = urllib.request.Request(BASE + path, method="OPTIONS", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization,Content-Type",
    })
    resp = urllib.request.urlopen(req)
    check(f"CORS OPTIONS {path}", resp.status, 204)

# ── User/Me ──
s, r = api("GET", "/user/me", token=tk)
check("GET /user/me", s, 200, f"has user={'user' in r.get('data',{})}, profile={'profile' in r.get('data',{})}")

# ── Profile Update ──
s, r = api("PUT", "/user/profile", token=tk, body={"first_name": "E2E", "company": "TestCo"})
check("PUT /user/profile", s, 200, f"first_name={r.get('data',{}).get('profile',{}).get('first_name')}")

# ── Settings ──
s, r = api("GET", "/settings", token=tk)
check("GET /settings", s, 200)

s, r = api("PUT", "/settings", token=tk, body={"theme": "dark", "notify_in_app": True})
check("PUT /settings", s, 200)

# ── Notifications ──
s, r = api("GET", "/notifications", token=tk)
check("GET /notifications", s, 200)

s, r = api("PATCH", "/notifications/read-all", token=tk)
check("PATCH /notifications/read-all", s, 200)

# ── Billing (public) ──
s, r = api("GET", "/billing/plans")
check("GET /billing/plans (public)", s, 200)

# ── Billing (auth) ──
s, r = api("GET", "/billing/subscription", token=tk)
check("GET /billing/subscription", s, 200)

s, r = api("GET", "/billing/tokens", token=tk)
check("GET /billing/tokens", s, 200)

s, r = api("GET", "/billing/transactions", token=tk)
check("GET /billing/transactions", s, 200)

# ── API Keys ──
s, r = api("GET", "/api-keys", token=tk)
check("GET /api-keys", s, 200)

# ── Chat ──
s, r = api("POST", "/chat", token=tk, body={"title": "E2E Test Chat", "prompt": "What is the meaning of life?"})
check("POST /chat", s, 201)
if s == 201:
    cid = r["data"]["id"]
    s2, _ = api("GET", "/chat/" + cid, token=tk)
    check("GET /chat/:id", s2, 200)

    s3, _ = api("GET", "/chat", token=tk)
    check("GET /chat (list)", s3, 200)

    s4, _ = api("PATCH", f"/chat/{cid}/rename", token=tk, body={"title": "Renamed"})
    check("PATCH /chat/:id/rename", s4, 200)

    s5, _ = api("DELETE", "/chat/" + cid, token=tk)
    check("DELETE /chat/:id", s5, 200)

# ── Contact (public) ──
s, r = api("POST", "/contact", body={"name":"Tester","email":"t@t.com","subject":"Test","message":"Hello"})
check("POST /contact (public)", s, 201)

# ── Summary ──
print(f"\n{'='*50}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL > 0:
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
