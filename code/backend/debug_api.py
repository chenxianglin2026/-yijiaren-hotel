"""Debug failing endpoints"""
import httpx
c = httpx.Client(timeout=10)
BASE = "http://localhost:8001"

# Login
r = c.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
tok = r.json()["access_token"]
print(f"Login OK, token={tok[:20]}...")

# Test GET /api/orders
print("\n=== GET /api/orders ===")
r = c.get(f"{BASE}/api/orders", headers={"Authorization": f"Bearer {tok}"})
print(f"status={r.status_code}, text_len={len(r.text)}")
print(f"text[:300]={r.text[:300]}")
try:
    print(f"json={r.json()}")
except Exception as e:
    print(f"json error: {e}")

# Test GET /api/cleaning/tasks no auth
print("\n=== GET /api/cleaning/tasks (no auth) ===")
r = c.get(f"{BASE}/api/cleaning/tasks")
print(f"status={r.status_code}, text_len={len(r.text)}")
print(f"text[:300]={r.text[:300]}")

# Test GET /docs
print("\n=== GET /docs ===")
r = c.get(f"{BASE}/docs")
print(f"status={r.status_code}, text_len={len(r.text)}")
print(f"content_type={r.headers.get('content-type','')}")
