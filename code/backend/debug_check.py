"""Debug checkin/order API issues"""
import httpx

BASE = "http://localhost:8001"

def main():
    # Login
    r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # Test orders/1/status
    r = httpx.post(f"{BASE}/api/orders/1/status", params={"new_status": "paid"}, headers=h)
    print(f"POST /api/orders/1/status: {r.status_code} {r.text[:300]}")

    # Test checkin list
    r = httpx.get(f"{BASE}/api/checkin", headers=h)
    print(f"GET /api/checkin: {r.status_code} {r.text[:300]}")

    # Test checkin/in
    r = httpx.post(f"{BASE}/api/checkin/in", json={"order_id": 1, "room_number": "101"}, headers=h)
    print(f"POST /api/checkin/in: {r.status_code} {r.text[:300]}")

    # List orders 
    r = httpx.get(f"{BASE}/api/orders", headers=h)
    print(f"GET /api/orders: {r.status_code} {r.text[:300]}")

    # Test openapi to see all routes
    r = httpx.get(f"{BASE}/openapi.json")
    spec = r.json()
    checkin_paths = [p for p in spec["paths"] if "checkin" in p]
    print(f"\nCheckin paths: {checkin_paths}")
    order_paths = [p for p in spec["paths"] if "order" in p.lower()]
    print(f"Order paths: {order_paths}")

if __name__ == "__main__":
    main()
