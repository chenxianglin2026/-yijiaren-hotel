"""
伊家人酒店系统 - 完整 API 测试 (pytest)
测试覆盖：认证 / 门店 / 房型 / 订单 / 入住 / 保洁 / 仪表盘 / 财务

运行方式：
  cd code/backend
  python -m pytest tests/api_test.py -v -s

前置条件：
  1. 服务器运行中: python app/main.py  (端口 8001)
  2. 已执行种子数据: python seed_mock.py
"""
import pytest
import httpx
import time
from datetime import date, timedelta

# ── 配置 ─────────────────────────────────────────────
BASE_URL = "http://localhost:8001"


class TestConfig:
    """测试共享状态"""
    admin_token: str = ""
    testuser_token: str = ""
    created_order_id: int = None
    created_task_id: int = None
    created_service_id: int = None


cfg = TestConfig()
client = httpx.Client(timeout=15)


# ══════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def check_server():
    """确保服务器在运行"""
    try:
        r = client.get(f"{BASE_URL}/health")
        assert r.status_code == 200, f"Server not reachable: {r.status_code}"
        print(f"\n✅ 服务器运行正常: {BASE_URL}")
    except httpx.ConnectError:
        pytest.exit(f"❌ 无法连接到 {BASE_URL}，请先启动服务器: python app/main.py")


@pytest.fixture(scope="session")
def admin_auth():
    """管理员登录"""
    if cfg.admin_token:
        return cfg.admin_token
    r = client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin", "password": "admin123"
    })
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    cfg.admin_token = r.json()["access_token"]
    return cfg.admin_token


@pytest.fixture(scope="session")
def testuser_auth():
    """普通用户登录"""
    if cfg.testuser_token:
        return cfg.testuser_token
    r = client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "testuser", "password": "test123"
    })
    assert r.status_code == 200, f"Testuser login failed: {r.text}"
    cfg.testuser_token = r.json()["access_token"]
    return cfg.testuser_token


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════
# 1. 系统健康检查
# ══════════════════════════════════════════════════════

class TestHealthCheck:
    """系统级别检查"""

    def test_root(self):
        r = client.get(f"{BASE_URL}/")
        assert r.status_code == 200
        data = r.json()
        assert "app" in data
        assert data["app"] == "伊家人酒店系统"

    def test_health(self):
        r = client.get(f"{BASE_URL}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_docs(self):
        r = client.get(f"{BASE_URL}/docs")
        assert r.status_code == 200

    def test_openapi_json(self):
        r = client.get(f"{BASE_URL}/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert "paths" in spec
        # 检查新增的仪表盘和财务端点
        paths = spec["paths"]
        assert "/api/dashboard/stats" in paths, "Dashboard stats endpoint missing"
        assert "/api/finance/daily" in paths, "Finance daily endpoint missing"
        assert "/api/finance/monthly" in paths, "Finance monthly endpoint missing"
        assert "/api/finance/reconciliation" in paths, "Finance reconciliation endpoint missing"
        assert "/api/finance/overview" in paths, "Finance overview endpoint missing"


# ══════════════════════════════════════════════════════
# 2. 认证 API
# ══════════════════════════════════════════════════════

class TestAuthAPI:
    """认证相关接口测试"""

    def test_login_admin(self, admin_auth):
        assert admin_auth is not None
        assert len(admin_auth) > 20

    def test_login_testuser(self, testuser_auth):
        assert testuser_auth is not None
        assert len(testuser_auth) > 20

    def test_login_wrong_password(self):
        r = client.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin", "password": "wrongpassword"
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = client.post(f"{BASE_URL}/api/auth/login", json={
            "username": "nonexistent_user_xyz", "password": "pass123"
        })
        assert r.status_code == 401

    def test_register_new_user(self):
        ts = int(time.time())
        r = client.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"apitest_{ts}",
            "password": "testpass123",
            "phone": f"138{ts % 100000000:08d}",
            "nickname": "API测试用户"
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["role"] == "guest"

    def test_register_duplicate_username(self):
        r = client.post(f"{BASE_URL}/api/auth/register", json={
            "username": "admin",
            "password": "pass1234",
            "phone": "13899999999"
        })
        assert r.status_code == 400

    def test_get_me(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/auth/me",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_get_me_unauthorized(self):
        r = client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code in (401, 403)

    def test_get_me_invalid_token(self):
        r = client.get(f"{BASE_URL}/api/auth/me",
                       headers=auth_header("invalid_token_xyz"))
        assert r.status_code == 401

    def test_wx_login_dev_mode(self):
        """开发模式下微信登录"""
        r = client.post(f"{BASE_URL}/api/auth/wx-login", json={
            "code": "test_wx_code_001",
            "nickname": "微信测试用户",
            "avatar_url": "https://avatar.example.com/001.jpg"
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data


# ══════════════════════════════════════════════════════
# 3. 门店 API
# ══════════════════════════════════════════════════════

class TestHotelsAPI:
    """门店与房型接口测试"""

    def test_list_hotels(self):
        r = client.get(f"{BASE_URL}/api/hotels")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        # 每个item应包含必要字段
        item = data["items"][0]
        assert "id" in item
        assert "name" in item
        assert "address" in item
        assert "city" in item
        assert "rating" in item
        assert "min_price" in item

    def test_list_hotels_filter_city(self):
        r = client.get(f"{BASE_URL}/api/hotels", params={"city": "杭州"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert "西湖" in data["items"][0]["name"]

    def test_list_hotels_filter_keyword(self):
        r = client.get(f"{BASE_URL}/api/hotels", params={"keyword": "三里屯"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        names = [h["name"] for h in data["items"]]
        assert any("三里屯" in n for n in names)

    def test_list_hotels_pagination(self):
        r = client.get(f"{BASE_URL}/api/hotels", params={"page": 1, "page_size": 2})
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 2
        assert data["total"] == 3

    def test_get_hotel_detail(self):
        r = client.get(f"{BASE_URL}/api/hotels/1")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert "name" in data
        assert "address" in data
        assert "rooms" in data
        assert len(data["rooms"]) == 5

    def test_get_hotel_not_found(self):
        r = client.get(f"{BASE_URL}/api/hotels/9999")
        assert r.status_code == 404

    def test_hotel_rooms_list(self):
        r = client.get(f"{BASE_URL}/api/hotels/1/rooms")
        assert r.status_code == 200
        rooms = r.json()
        assert len(rooms) == 5
        room = rooms[0]
        assert "name" in room
        assert "price" in room
        assert "room_type" in room
        assert "available_count" in room

    def test_room_detail(self):
        r = client.get(f"{BASE_URL}/api/hotels/rooms/1")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert data["name"] is not None


# ══════════════════════════════════════════════════════
# 4. 房态 API
# ══════════════════════════════════════════════════════

class TestRoomsAPI:
    """房态管理接口测试"""

    def test_room_status_all(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/rooms/status", headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total_rooms" in data
        assert "available_total" in data
        assert data["total_rooms"] > 0

    def test_room_status_by_hotel(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/rooms/status", params={"hotel_id": 1}, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) > 0
        # 检查每个item的字段
        item = data["items"][0]
        assert "booked_count" in item
        assert "occupied_count" in item
        assert "cleaning_count" in item

    def test_room_status_invalid_hotel(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/rooms/status", params={"hotel_id": 9999}, headers=auth_header(admin_auth))
        assert r.status_code == 404


# ══════════════════════════════════════════════════════
# 5. 订单 API
# ══════════════════════════════════════════════════════

class TestOrdersAPI:
    """订单接口测试"""

    def test_create_order(self, admin_auth):
        today = date.today()
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1,
            "room_id": 1,
            "room_count": 1,
            "checkin_date": (today + timedelta(days=5)).isoformat(),
            "checkout_date": (today + timedelta(days=7)).isoformat(),
            "guest_name": "API测试",
            "guest_phone": "13800000001"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 201, f"Create order failed: {r.text}"
        data = r.json()
        assert "order_no" in data
        assert data["status"] == "pending"
        assert data["nights"] == 2
        assert data["total_price"] > 0
        cfg.created_order_id = data["id"]

    def test_create_order_past_date(self, admin_auth):
        today = date.today()
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1,
            "room_id": 1,
            "room_count": 1,
            "checkin_date": (today - timedelta(days=1)).isoformat(),
            "checkout_date": (today + timedelta(days=1)).isoformat(),
            "guest_name": "API测试",
            "guest_phone": "13800000001"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_create_order_invalid_dates(self, admin_auth):
        today = date.today()
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1,
            "room_id": 1,
            "room_count": 1,
            "checkin_date": (today + timedelta(days=5)).isoformat(),
            "checkout_date": (today + timedelta(days=3)).isoformat(),  # 早于入住
            "guest_name": "API测试",
            "guest_phone": "13800000001"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_list_orders(self, testuser_auth):
        r = client.get(f"{BASE_URL}/api/orders",
                       headers=auth_header(testuser_auth))
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 2  # testuser有至少2个订单

    def test_list_orders_filter_status(self, testuser_auth):
        r = client.get(f"{BASE_URL}/api/orders",
                       params={"status": "pending"},
                       headers=auth_header(testuser_auth))
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            assert item["status"] == "pending"

    def test_get_order_detail(self, admin_auth):
        if cfg.created_order_id:
            r = client.get(f"{BASE_URL}/api/orders/{cfg.created_order_id}",
                           headers=auth_header(admin_auth))
            assert r.status_code == 200

    def test_cancel_order(self, admin_auth):
        if cfg.created_order_id:
            r = client.post(
                f"{BASE_URL}/api/orders/{cfg.created_order_id}/cancel",
                params={"reason": "测试取消"},
                headers=auth_header(admin_auth)
            )
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "cancelled"


# ══════════════════════════════════════════════════════
# 6. 保洁 API
# ══════════════════════════════════════════════════════

class TestCleaningAPI:
    """保洁管理接口测试"""

    def test_create_cleaning_task(self, admin_auth):
        r = client.post(f"{BASE_URL}/api/cleaning/tasks", json={
            "hotel_id": 1,
            "room_number": "301",
            "task_type": "cleanup",
            "notes": "退房打扫"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Create task failed: {r.text}"
        data = r.json()
        assert data["status"] == "pending"
        cfg.created_task_id = data["id"]

    def test_list_cleaning_tasks(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/cleaning/tasks",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    def test_cleaning_task_detail(self, admin_auth):
        if cfg.created_task_id:
            r = client.get(f"{BASE_URL}/api/cleaning/tasks/{cfg.created_task_id}",
                           headers=auth_header(admin_auth))
            assert r.status_code == 200

    def test_accept_cleaning_task(self, admin_auth):
        if cfg.created_task_id:
            r = client.post(f"{BASE_URL}/api/cleaning/tasks/accept", json={
                "task_id": cfg.created_task_id
            }, headers=auth_header(admin_auth))
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "accepted"

    def test_start_cleaning(self, admin_auth):
        if cfg.created_task_id:
            r = client.post(f"{BASE_URL}/api/cleaning/tasks/start", json={
                "task_id": cfg.created_task_id
            }, headers=auth_header(admin_auth))
            assert r.status_code == 200
            assert r.json()["status"] == "in_progress"

    def test_complete_cleaning(self, admin_auth):
        if cfg.created_task_id:
            r = client.post(f"{BASE_URL}/api/cleaning/tasks/complete", json={
                "task_id": cfg.created_task_id,
                "photo_urls": '["https://img.example.com/clean/301.jpg"]',
                "notes": "打扫完成"
            }, headers=auth_header(admin_auth))
            assert r.status_code == 200
            assert r.json()["status"] == "completed"

    def test_create_service_request(self, admin_auth):
        r = client.post(f"{BASE_URL}/api/cleaning/service", json={
            "hotel_id": 1,
            "room_number": "101",
            "request_type": "delivery",
            "description": "需要拖鞋和矿泉水",
            "priority": "normal"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Create service failed: {r.text}"
        data = r.json()
        cfg.created_service_id = data["id"]

    def test_list_service_requests(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/cleaning/service",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    def test_service_stats(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/cleaning/service-stats",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "cleaning" in data
        assert "delivery" in data
        assert "maintenance" in data

    def test_accept_service_request(self, admin_auth):
        if cfg.created_service_id:
            r = client.post(
                f"{BASE_URL}/api/cleaning/service/{cfg.created_service_id}/accept",
                headers=auth_header(admin_auth))
            assert r.status_code == 200
            assert r.json()["status"] == "accepted"

    def test_complete_service_request(self, admin_auth):
        if cfg.created_service_id:
            r = client.post(
                f"{BASE_URL}/api/cleaning/service/{cfg.created_service_id}/complete",
                json={"remark": "已完成"},
                headers=auth_header(admin_auth))
            assert r.status_code in (200, 400)  # 可能已经是in_progress或accepted


# ══════════════════════════════════════════════════════
# 7. 仪表盘 API
# ══════════════════════════════════════════════════════

class TestDashboardAPI:
    """仪表盘统计接口测试"""

    def test_dashboard_stats_global(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/dashboard/stats",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Dashboard stats failed: {r.text}"
        data = r.json()
        assert data["code"] == 0, f"Expected code=0, got: {data}"
        stats = data["data"]
        # 验证必要字段存在
        assert "total_rooms" in stats, f"Missing total_rooms in: {stats}"
        assert "occupied_rooms" in stats
        assert "occupancy_rate" in stats
        assert "orders_today" in stats
        assert "revenue_today" in stats
        assert "checked_in_count" in stats
        assert "pending_cleaning_count" in stats
        # 验证数值合理性
        assert stats["total_rooms"] > 0, "total_rooms should be > 0"
        assert stats["occupied_rooms"] >= 0
        assert 0 <= stats["occupancy_rate"] <= 100
        assert stats["revenue_today"] >= 0

    def test_dashboard_stats_by_hotel(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/dashboard/stats",
                       params={"hotel_id": 1},
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        stats = data["data"]
        assert stats["hotel_id"] == 1
        assert stats["hotel_name"] is not None

    def test_dashboard_stats_invalid_hotel(self, admin_auth):
        r = client.get(f"{BASE_URL}/api/dashboard/stats",
                       params={"hotel_id": 9999},
                       headers=auth_header(admin_auth))
        assert r.status_code == 404

    def test_dashboard_requires_auth(self):
        r = client.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


# ══════════════════════════════════════════════════════
# 8. 财务 API
# ══════════════════════════════════════════════════════

class TestFinanceAPI:
    """财务接口测试"""

    def test_finance_daily_revenue(self, admin_auth):
        """日营收报表"""
        today = date.today()
        r = client.get(f"{BASE_URL}/api/finance/daily", params={
            "start_date": (today - timedelta(days=7)).isoformat(),
            "end_date": today.isoformat(),
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Daily revenue failed: {r.text}"
        data = r.json()
        assert data["code"] == 0
        assert "data" in data
        assert "summary" in data
        summary = data["summary"]
        assert "total_revenue" in summary
        assert "total_orders" in summary
        assert isinstance(data["data"], list)

    def test_finance_daily_by_hotel(self, admin_auth):
        """按门店日营收"""
        today = date.today()
        r = client.get(f"{BASE_URL}/api/finance/daily", params={
            "start_date": (today - timedelta(days=30)).isoformat(),
            "end_date": today.isoformat(),
            "hotel_id": 1,
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert len(data["data"]) > 0

    def test_finance_daily_invalid_date(self, admin_auth):
        """非法日期"""
        r = client.get(f"{BASE_URL}/api/finance/daily", params={
            "start_date": "invalid-date",
            "end_date": "2026-01-01",
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_finance_monthly_revenue(self, admin_auth):
        """月营收报表"""
        today = date.today()
        r = client.get(f"{BASE_URL}/api/finance/monthly", params={
            "year": today.year,
            "month": today.month,
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Monthly revenue failed: {r.text}"
        data = r.json()
        assert data["code"] == 0
        item = data["data"]
        assert item["year"] == today.year
        assert item["month"] == today.month
        assert "total_orders" in item
        assert "revenue" in item
        assert "paid_orders" in item

    def test_finance_monthly_by_hotel(self, admin_auth):
        """按门店月营收"""
        today = date.today()
        r = client.get(f"{BASE_URL}/api/finance/monthly", params={
            "year": today.year,
            "month": today.month,
            "hotel_id": 1,
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_finance_monthly_invalid(self, admin_auth):
        """非法月份"""
        r = client.get(f"{BASE_URL}/api/finance/monthly", params={
            "year": 2026,
            "month": 13,
        }, headers=auth_header(admin_auth))
        assert r.status_code == 422  # FastAPI validation error

    def test_finance_reconciliation(self, admin_auth):
        """支付对账报表"""
        today = date.today()
        r = client.get(f"{BASE_URL}/api/finance/reconciliation", params={
            "start_date": (today - timedelta(days=30)).isoformat(),
            "end_date": today.isoformat(),
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Reconciliation failed: {r.text}"
        data = r.json()
        assert data["code"] == 0
        assert "data" in data
        assert "summary" in data
        summary = data["summary"]
        assert "total_count" in summary
        assert "total_amount" in summary
        assert "paid_count" in summary
        assert "pending_count" in summary

    def test_finance_reconciliation_by_status(self, admin_auth):
        """按状态筛选对账"""
        today = date.today()
        r = client.get(f"{BASE_URL}/api/finance/reconciliation", params={
            "start_date": (today - timedelta(days=30)).isoformat(),
            "end_date": today.isoformat(),
            "status": "paid",
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        for item in data["data"]:
            assert item["status"] == "paid"

    def test_finance_overview(self, admin_auth):
        """财务总览"""
        r = client.get(f"{BASE_URL}/api/finance/overview",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Overview failed: {r.text}"
        data = r.json()
        assert data["code"] == 0
        overview = data["data"]
        assert "today" in overview
        assert "this_month" in overview
        assert "total" in overview
        assert "current_checkins" in overview
        # 验证today字段
        assert "revenue" in overview["today"]
        assert "orders" in overview["today"]
        assert "date" in overview["today"]
        # 验证this_month字段
        assert "revenue" in overview["this_month"]
        # 验证total字段
        assert "revenue" in overview["total"]

    def test_finance_overview_by_hotel(self, admin_auth):
        """按门店财务总览"""
        r = client.get(f"{BASE_URL}/api/finance/overview",
                       params={"hotel_id": 1},
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0


# ══════════════════════════════════════════════════════
# 9. 入住管理 API
# ══════════════════════════════════════════════════════

class TestCheckinAPI:
    """入住管理接口测试"""

    def test_checkin_unpaid_order(self, testuser_auth):
        """尝试用未支付订单办理入住（应失败）"""
        # 获取testuser的pending订单
        r_orders = client.get(f"{BASE_URL}/api/orders",
                              headers=auth_header(testuser_auth))
        orders = r_orders.json().get("items", [])
        pending_order = next((o for o in orders if o["status"] == "pending"), None)
        if pending_order:
            r = client.post(f"{BASE_URL}/api/checkin/in", json={
                "order_id": pending_order["id"],
                "room_number": "101"
            }, headers=auth_header(testuser_auth))
            assert r.status_code == 400  # 未支付不能入住


# ══════════════════════════════════════════════════════
# 运行入口
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
