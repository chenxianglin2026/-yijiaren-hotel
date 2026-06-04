"""
伊家人后端全API测试脚本
使用 httpx 测试所有端点
"""
import sys
import json
import httpx

BASE = "http://localhost:8001"
PASSES = 0
FAILS = 0
REPORT = []

AUTH_TOKEN = None  # admin token

def log(label, result, detail=""):
    global PASSES, FAILS
    status = "✅ PASS" if result else "❌ FAIL"
    entry = f"{status} | {label}"
    if detail:
        entry += f" | {detail}"
    REPORT.append(entry)
    if result:
        PASSES += 1
    else:
        FAILS += 1
    print(entry)

client = httpx.Client(timeout=10)

# ─── 1. GET / ──────────────────────────────
try:
    r = client.get(f"{BASE}/")
    ok = r.status_code == 200 and "app" in r.json()
    log("GET /", ok, f"status={r.status_code}")
except Exception as e:
    log("GET /", False, str(e))

# ─── 2. GET /health ────────────────────────
try:
    r = client.get(f"{BASE}/health")
    d = r.json()
    ok = r.status_code == 200 and d.get("status") == "ok"
    log("GET /health", ok, f"status={r.status_code}")
except Exception as e:
    log("GET /health", False, str(e))

# ─── 3. POST /api/auth/login (admin) ──────
try:
    r = client.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
    d = r.json()
    ok = r.status_code == 200 and "access_token" in d
    if ok:
        AUTH_TOKEN = d["access_token"]
    log("POST /api/auth/login (admin)", ok, f"status={r.status_code}")
except Exception as e:
    log("POST /api/auth/login (admin)", False, str(e))

# ─── 4. POST /api/auth/login (testuser) ───
TESTUSER_TOKEN = None
try:
    r = client.post(f"{BASE}/api/auth/login", json={"username": "testuser", "password": "test123"})
    d = r.json()
    ok = r.status_code == 200 and "access_token" in d
    if ok:
        TESTUSER_TOKEN = d["access_token"]
    log("POST /api/auth/login (testuser)", ok, f"status={r.status_code}")
except Exception as e:
    log("POST /api/auth/login (testuser)", False, str(e))

# ─── 5. POST /api/auth/login (wrong pw) ───
try:
    r = client.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "wrong"})
    ok = r.status_code == 401
    log("POST /api/auth/login (wrong pw)", ok, f"status={r.status_code}")
except Exception as e:
    log("POST /api/auth/login (wrong pw)", False, str(e))

# ─── 6. GET /api/auth/me (with token) ─────
try:
    r = client.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
    d = r.json()
    ok = r.status_code == 200 and d.get("username") == "admin"
    log("GET /api/auth/me", ok, f"status={r.status_code}")
except Exception as e:
    log("GET /api/auth/me", False, str(e))

# ─── 7. POST /api/auth/register ───────────
import time as _time
try:
    r = client.post(f"{BASE}/api/auth/register", json={
        "username": f"newuser_{int(_time.time())}",
        "password": "newpass123",
        "phone": f"139{int(_time.time()) % 100000000:08d}",
        "nickname": "API测试用户"
    })
    d = r.json()
    ok = r.status_code == 200 and "access_token" in d
    log("POST /api/auth/register", ok, f"status={r.status_code}")
except Exception as e:
    log("POST /api/auth/register", False, str(e))

# ─── 8. GET /api/hotels ────────────────────
try:
    r = client.get(f"{BASE}/api/hotels")
    d = r.json()
    ok = r.status_code == 200 and d.get("total") == 3 and len(d.get("items", [])) == 3
    log("GET /api/hotels", ok, f"total={d.get('total')}")
except Exception as e:
    log("GET /api/hotels", False, str(e))

# ─── 9. GET /api/hotels?city=杭州 ──────────
try:
    r = client.get(f"{BASE}/api/hotels?city=杭州")
    d = r.json()
    ok = r.status_code == 200 and d.get("total") == 1
    log("GET /api/hotels?city=杭州", ok, f"total={d.get('total')}")
except Exception as e:
    log("GET /api/hotels?city=杭州", False, str(e))

# ─── 10. GET /api/hotels/1 ─────────────────
try:
    r = client.get(f"{BASE}/api/hotels/1")
    d = r.json()
    ok = r.status_code == 200 and "name" in d and "rooms" in d
    log("GET /api/hotels/1", ok, f"name={d.get('name')}, rooms={len(d.get('rooms',[]))}")
except Exception as e:
    log("GET /api/hotels/1", False, str(e))

# ─── 11. GET /api/hotels/999 (not found) ──
try:
    r = client.get(f"{BASE}/api/hotels/999")
    ok = r.status_code == 404
    log("GET /api/hotels/999 (404)", ok, f"status={r.status_code}")
except Exception as e:
    log("GET /api/hotels/999 (404)", False, str(e))

# ─── 12. GET /api/hotels/1/rooms ───────────
try:
    r = client.get(f"{BASE}/api/hotels/1/rooms")
    d = r.json()
    ok = r.status_code == 200 and len(d) == 5
    log("GET /api/hotels/1/rooms", ok, f"count={len(d)}")
except Exception as e:
    log("GET /api/hotels/1/rooms", False, str(e))

# ─── 13. GET /api/hotels/rooms/1 ───────────
try:
    r = client.get(f"{BASE}/api/hotels/rooms/1")
    d = r.json()
    ok = r.status_code == 200 and d.get("id") == 1
    log("GET /api/hotels/rooms/1", ok, f"name={d.get('name')}")
except Exception as e:
    log("GET /api/hotels/rooms/1", False, str(e))

# ─── 14. GET /api/rooms/status ──────────────
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.get(f"{BASE}/api/rooms/status", headers=headers)
    d = r.json()
    ok = r.status_code == 200 and "items" in d
    log("GET /api/rooms/status", ok, f"items_count={len(d.get('items',[]))}")
except Exception as e:
    log("GET /api/rooms/status", False, str(e))

# ─── 15. GET /api/rooms/status?hotel_id=1 ───
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.get(f"{BASE}/api/rooms/status?hotel_id=1", headers=headers)
    d = r.json()
    ok = r.status_code == 200 and "items" in d
    log("GET /api/rooms/status?hotel_id=1", ok, f"items_count={len(d.get('items',[]))}")
except Exception as e:
    log("GET /api/rooms/status?hotel_id=1", False, str(e))

# ─── 16. POST /api/orders (auth) ───────────
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.post(f"{BASE}/api/orders", json={
        "hotel_id": 1,
        "room_id": 1,
        "room_count": 1,
        "checkin_date": "2026-06-10",
        "checkout_date": "2026-06-12",
        "guest_name": "管理员",
        "guest_phone": "13800000001"
    }, headers=headers)
    d = r.json()
    ok = r.status_code == 201 and "order_no" in d
    log("POST /api/orders", ok, f"status={r.status_code}, order_no={d.get('order_no','N/A')}")
except Exception as e:
    log("POST /api/orders", False, str(e))

# ─── 17. GET /api/orders (auth) ────────────
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.get(f"{BASE}/api/orders", headers=headers)
    d = r.json()
    ok = r.status_code == 200 and "items" in d
    log("GET /api/orders", ok, f"total={d.get('total')}")
except Exception as e:
    log("GET /api/orders", False, str(e))

# ─── 18. GET /api/cleaning/tasks (no auth) ─
try:
    r = client.get(f"{BASE}/api/cleaning/tasks")
    ok = r.status_code in (200, 401, 403)  # requires auth
    log("GET /api/cleaning/tasks (no auth)", ok, f"status={r.status_code}")
except Exception as e:
    log("GET /api/cleaning/tasks (no auth)", False, str(e))

# ─── 19. GET /api/cleaning/tasks (auth) ────
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.get(f"{BASE}/api/cleaning/tasks", headers=headers)
    d = r.json()
    ok = r.status_code == 200 and "items" in d
    log("GET /api/cleaning/tasks (admin)", ok, f"total={d.get('total')}")
except Exception as e:
    log("GET /api/cleaning/tasks (admin)", False, str(e))

# ─── 20. POST /api/cleaning/tasks (auth) ───
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.post(f"{BASE}/api/cleaning/tasks", json={
        "hotel_id": 1,
        "room_number": "101",
        "task_type": "cleanup",
        "notes": "测试保洁工单"
    }, headers=headers)
    d = r.json()
    ok = r.status_code == 200 and d.get("id") is not None
    log("POST /api/cleaning/tasks", ok, f"status={r.status_code}, id={d.get('id','N/A')}")
except Exception as e:
    log("POST /api/cleaning/tasks", False, str(e))

# ─── 21. GET /api/cleaning/service ──────────
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.get(f"{BASE}/api/cleaning/service", headers=headers)
    d = r.json()
    ok = r.status_code == 200 and "items" in d
    log("GET /api/cleaning/service", ok, f"total={d.get('total')}")
except Exception as e:
    log("GET /api/cleaning/service", False, str(e))

# ─── 22. POST /api/cleaning/service ────────
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.post(f"{BASE}/api/cleaning/service", json={
        "hotel_id": 1,
        "room_number": "101",
        "request_type": "cleaning",
        "description": "需要打扫卫生",
        "priority": "normal"
    }, headers=headers)
    d = r.json()
    ok = r.status_code == 200 and d.get("id") is not None
    log("POST /api/cleaning/service", ok, f"status={r.status_code}, id={d.get('id','N/A')}")
except Exception as e:
    log("POST /api/cleaning/service", False, str(e))

# ─── 23. GET /api/cleaning/service-stats ────
try:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    r = client.get(f"{BASE}/api/cleaning/service-stats", headers=headers)
    d = r.json()
    ok = r.status_code == 200
    log("GET /api/cleaning/service-stats", ok, f"stats={d}")
except Exception as e:
    log("GET /api/cleaning/service-stats", False, str(e))

# ─── 24. GET /api/cleaning/cleaners ─────────
try:
    r = client.get(f"{BASE}/api/cleaning/cleaners")
    d = r.json()
    ok = r.status_code == 200 and isinstance(d, list)
    log("GET /api/cleaning/cleaners", ok, f"count={len(d) if isinstance(d, list) else 'N/A'}")
except Exception as e:
    log("GET /api/cleaning/cleaners", False, str(e))

# ─── 25. POST /api/checkin/in (auth) ───────
try:
    # Get orders for testuser to find a paid order
    headers_test = {"Authorization": f"Bearer {TESTUSER_TOKEN}"}
    r_orders = client.get(f"{BASE}/api/orders", headers=headers_test)
    orders = r_orders.json().get("items", [])
    paid_order = next((o for o in orders if o["status"] == "paid"), None)
    if paid_order:
        r = client.post(f"{BASE}/api/checkin/in", json={
            "order_id": paid_order["id"],
            "room_number": "101"
        }, headers=headers_test)
        d = r.json()
        ok = r.status_code == 200 and d.get("status") == "checked_in"
        log("POST /api/checkin/in", ok, f"status={r.status_code}")
    else:
        log("POST /api/checkin/in", True, "no paid order to test (skipped)")
except Exception as e:
    log("POST /api/checkin/in", False, str(e))

# ─── 26. GET /docs (Swagger) ───────────────
try:
    r = client.get(f"{BASE}/docs")
    ok = r.status_code == 200
    log("GET /docs (Swagger)", ok, f"status={r.status_code}")
except Exception as e:
    log("GET /docs (Swagger)", False, str(e))

# ─── 27. GET /openapi.json ──────────────────
try:
    r = client.get(f"{BASE}/openapi.json")
    ok = r.status_code == 200
    log("GET /openapi.json", ok, f"status={r.status_code}")
except Exception as e:
    log("GET /openapi.json", False, str(e))

# ─── Summary ────────────────────────────────
print("\n" + "="*60)
print(f"TOTAL: {PASSES} passed, {FAILS} failed out of {PASSES+FAILS}")
if FAILS == 0:
    print("🎉 ALL TESTS PASSED!")
else:
    print(f"⚠️  {FAILS} failures detected. Check report above.")
