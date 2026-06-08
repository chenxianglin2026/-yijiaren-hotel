"""Quick smoke test for new endpoints"""
import httpx, json

BASE = "http://localhost:8001"

# Login
r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
assert r.status_code == 200, f"Login failed: {r.text}"
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Test devices list
r = httpx.get(f"{BASE}/api/devices/list", headers=h)
j = r.json()
print("=== Devices List ===")
assert j["code"] == 0
assert j["total"] == 8
assert j["online_count"] > 0
print(f"  PASS: {j['total']} devices, {j['online_count']} online, {j['offline_count']} offline, {j['alert_count']} alert")

# Test devices stats
r2 = httpx.get(f"{BASE}/api/devices/stats", headers=h)
j2 = r2.json()
assert j2["code"] == 0
print(f"  PASS: stats - total={j2['data']['total']}, low_battery={j2['data']['low_battery']}")

# Test dashboard perf
r3 = httpx.get(f"{BASE}/api/dashboard/perf", headers=h)
j3 = r3.json()
assert j3["code"] == 0
assert "api_calls_before" in j3["data"]
print(f"  PASS: perf endpoint")

# Test db-pool enhanced
r4 = httpx.get(f"{BASE}/api/system/db-pool", headers=h)
j4 = r4.json()
assert j4["code"] == 0
assert "status" in j4["data"]
assert "usage_pct" in j4["data"]
print(f"  PASS: db-pool - status={j4['data']['status']}, msg={j4['data']['status_msg']}")

# Test heartbeat
r5 = httpx.post(f"{BASE}/api/devices/heartbeat", json={
    "device_id": "LOCK-001",
    "status": "online",
    "battery": 80,
}, headers=h)
j5 = r5.json()
assert j5["code"] == 0
print(f"  PASS: heartbeat for LOCK-001")

# Test register new device
r6 = httpx.post(f"{BASE}/api/devices/register", json={
    "device_id": "TEST-LOCK-99",
    "name": "测试门锁",
    "device_type": "smart_lock",
    "hotel_id": 1,
    "room_number": "999",
}, headers=h)
j6 = r6.json()
assert j6["code"] == 0
print(f"  PASS: registered TEST-LOCK-99")

# Verify all 8 + 1 = 9 devices now
r7 = httpx.get(f"{BASE}/api/devices/list", headers=h)
j7 = r7.json()
assert j7["total"] >= 9
print(f"  PASS: total devices now {j7['total']}")

print("\n✅ ALL SMOKE TESTS PASSED")
