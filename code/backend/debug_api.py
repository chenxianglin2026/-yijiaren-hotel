#!/usr/bin/env python3
"""Debug script to check API endpoints"""
import httpx
c = httpx.Client(timeout=10)
BASE = "http://localhost:8001"

# Login
r = c.post(f"{BASE}/api/auth/login", json={"username":"admin","password":"admin123"})
assert r.status_code == 200, f"Login failed: {r.text}"
t = r.json()["access_token"]
h = {"Authorization": f"Bearer {t}"}

# Checkin list
r = c.get(f"{BASE}/api/checkin", headers=h)
print(f"GET /api/checkin: {r.status_code}")
if r.status_code != 200:
    print(f"  Body: {r.text[:300]}")

# Order status update - try with an existing order
r = c.get(f"{BASE}/api/orders?page_size=1", headers=h)
orders = r.json().get("items", [])
if orders:
    oid = orders[0]["id"]
    ostatus = orders[0]["status"]
    print(f"  Found order {oid}, current status={ostatus}")
    # Try status update
    r2 = c.post(f"{BASE}/api/orders/{oid}/status?new_status=cancelled", headers=h)
    print(f"  POST /api/orders/{oid}/status?new_status=cancelled: {r2.status_code}")
    if r2.status_code != 200:
        print(f"    Body: {r2.text[:300]}")

# Room availability
r = c.get(f"{BASE}/api/hotels/1/rooms")
rooms = r.json()
print("\nRoom availability (hotel 1):")
for rm in rooms:
    print(f"  Room {rm['id']} ({rm['name']}): available={rm['available_count']}")

# Check hotel 2
r = c.get(f"{BASE}/api/hotels/2/rooms")
rooms2 = r.json()
print("\nRoom availability (hotel 2):")
for rm in rooms2:
    print(f"  Room {rm['id']} ({rm['name']}): available={rm['available_count']}")

# Check available orders count 
r = c.get(f"{BASE}/api/orders", headers=h)
print(f"\nTotal orders: {r.json().get('total', 'N/A')}")
