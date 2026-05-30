"""Quick test: register with unique name"""
import httpx, time
c = httpx.Client(timeout=10)
BASE = "http://localhost:8001"

uname = f"test_{int(time.time())}"
r = c.post(f"{BASE}/api/auth/register", json={
    "username": uname,
    "password": "pass123456",
    "phone": "13900008888",
    "nickname": "Fresh Test"
})
print(f"status={r.status_code}")
print(f"body={r.text[:500]}")
