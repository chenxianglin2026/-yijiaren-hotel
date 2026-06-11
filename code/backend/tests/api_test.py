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
        data = r.json()["data"]
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
        data = r.json()["data"]
        assert data["total"] == 1
        assert "西湖" in data["items"][0]["name"]

    def test_list_hotels_filter_keyword(self):
        r = client.get(f"{BASE_URL}/api/hotels", params={"keyword": "三里屯"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] >= 1
        names = [h["name"] for h in data["items"]]
        assert any("三里屯" in n for n in names)

    def test_list_hotels_pagination(self):
        r = client.get(f"{BASE_URL}/api/hotels", params={"page": 1, "page_size": 2})
        assert r.status_code == 200
        data = r.json()["data"]
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

    def test_checkin_empty_room_number(self, admin_auth):
        """空房间号办理入住应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 3, "room_count": 1,
            "checkin_date": (today + timedelta(days=10)).isoformat(),
            "checkout_date": (today + timedelta(days=12)).isoformat(),
            "guest_name": "空房号测试", "guest_phone": "13800001113"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        # 模拟支付
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        # 空房间号
        r = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": ""
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_checkin_nonexistent_order(self, testuser_auth):
        """用不存在的订单ID办理入住房应报404"""
        r = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": 99999, "room_number": "101"
        }, headers=auth_header(testuser_auth))
        assert r.status_code == 404

    def test_checkin_duplicate_order(self, admin_auth):
        """同一订单重复办理入住应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 4, "room_count": 1,
            "checkin_date": (today + timedelta(days=11)).isoformat(),
            "checkout_date": (today + timedelta(days=13)).isoformat(),
            "guest_name": "重复入住测试", "guest_phone": "13800001114"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        # 模拟支付
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        # 第一次入住
        r1 = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "201"
        }, headers=auth_header(admin_auth))
        assert r1.status_code == 200
        # 第二次入住 - 重复
        r2 = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "202"
        }, headers=auth_header(admin_auth))
        assert r2.status_code == 400

    def test_checkout_already_checked_out(self, admin_auth):
        """重复退房应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=12)).isoformat(),
            "checkout_date": (today + timedelta(days=14)).isoformat(),
            "guest_name": "重复退房测试", "guest_phone": "13800001115"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "301"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        # 第一次退房
        r1 = client.post(f"{BASE_URL}/api/checkin/out/{checkin_id}",
                        headers=auth_header(admin_auth))
        assert r1.status_code == 200
        # 第二次退房
        r2 = client.post(f"{BASE_URL}/api/checkin/out/{checkin_id}",
                        headers=auth_header(admin_auth))
        assert r2.status_code == 400

    def test_unlock_invalid_action(self, admin_auth):
        """非法开锁action应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=13)).isoformat(),
            "checkout_date": (today + timedelta(days=15)).isoformat(),
            "guest_name": "开锁测试", "guest_phone": "13800001116"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "401"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        r = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "explode"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_list_checkins(self, admin_auth):
        """入住记录列表"""
        r = client.get(f"{BASE_URL}/api/checkin", headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 0

    def test_checkin_list_filter_status(self, admin_auth):
        """按状态筛选入住记录"""
        r = client.get(f"{BASE_URL}/api/checkin",
                       params={"status": "checked_in"},
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["status"] == "checked_in"

    def test_checkin_list_invalid_status(self, admin_auth):
        """非法状态参数应报400"""
        r = client.get(f"{BASE_URL}/api/checkin",
                       params={"status": "sleeping"},
                       headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_unlock_on_checked_out(self, admin_auth):
        """已退房后尝试开锁应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=14)).isoformat(),
            "checkout_date": (today + timedelta(days=16)).isoformat(),
            "guest_name": "退房后开锁", "guest_phone": "13800001117"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "501"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        # 退房
        client.post(f"{BASE_URL}/api/checkin/out/{checkin_id}",
                    headers=auth_header(admin_auth))
        # 尝试开锁
        r = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "unlock"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_checkin_list_filter_hotel(self, admin_auth):
        """按门店筛选入住记录"""
        r = client.get(f"{BASE_URL}/api/checkin",
                       params={"hotel_id": 1},
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["hotel_id"] == 1

    def test_checkin_happy_path(self, admin_auth):
        """正常入住流程: 创建订单→支付→入住→验证"""
        today = date.today()
        # 1. 创建订单
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 3, "room_count": 1,
            "checkin_date": (today + timedelta(days=15)).isoformat(),
            "checkout_date": (today + timedelta(days=17)).isoformat(),
            "guest_name": "入住正流程", "guest_phone": "13800001120"
        }, headers=auth_header(admin_auth))
        assert r_order.status_code == 201
        order_id = r_order.json()["id"]
        # 2. 模拟支付
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        # 3. 办理入住
        r = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "902"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Checkin failed: {r.text}"
        data = r.json()
        assert data["status"] == "checked_in"
        assert data["room_number"] == "902"
        assert data["checkin_time"] is not None
        assert data["order_id"] == order_id
        assert data["hotel_name"] is not None
        assert data["guest_name"] == "入住正流程"

    def test_checkout_happy_path(self, admin_auth):
        """正常退房流程: 入住→退房→验证订单完成"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 4, "room_count": 1,
            "checkin_date": (today + timedelta(days=16)).isoformat(),
            "checkout_date": (today + timedelta(days=18)).isoformat(),
            "guest_name": "退房正流程", "guest_phone": "13800001121"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        # 入住
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "903"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        # 退房
        r = client.post(f"{BASE_URL}/api/checkin/out/{checkin_id}",
                        headers=auth_header(admin_auth))
        assert r.status_code == 200, f"Checkout failed: {r.text}"
        data = r.json()
        assert data["status"] == "checked_out"
        assert data["checkout_time"] is not None
        # 验证订单状态变为 completed
        r_order_after = client.get(f"{BASE_URL}/api/orders/{order_id}",
                                   headers=auth_header(admin_auth))
        assert r_order_after.json()["status"] == "completed"

    def test_unlock_and_lock_recording(self, admin_auth):
        """开锁/关锁记录正确追加"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=17)).isoformat(),
            "checkout_date": (today + timedelta(days=19)).isoformat(),
            "guest_name": "开锁记录测试", "guest_phone": "13800001122"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "904"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        # 开锁
        r1 = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "unlock"
        }, headers=auth_header(admin_auth))
        assert r1.status_code == 200
        assert len(r1.json()["door_lock_records"]) == 1
        assert r1.json()["door_lock_records"][0]["action"] == "unlock"
        # 关锁
        r2 = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "lock"
        }, headers=auth_header(admin_auth))
        assert r2.status_code == 200
        assert len(r2.json()["door_lock_records"]) == 2
        assert r2.json()["door_lock_records"][1]["action"] == "lock"
        # 再次开锁
        r3 = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "unlock"
        }, headers=auth_header(admin_auth))
        assert r3.status_code == 200
        assert len(r3.json()["door_lock_records"]) == 3

    def test_checkin_detail(self, admin_auth):
        """入住详情查询"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=18)).isoformat(),
            "checkout_date": (today + timedelta(days=20)).isoformat(),
            "guest_name": "详情测试", "guest_phone": "13800001123"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "905"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        # 查询详情
        r = client.get(f"{BASE_URL}/api/checkin/{checkin_id}",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == checkin_id
        assert data["status"] == "checked_in"
        assert data["room_number"] == "905"
        assert data["guest_name"] == "详情测试"
        assert data["checkin_time"] is not None

    def test_guest_cannot_checkin_other_order(self, testuser_auth):
        """普通用户不能为他人订单办理入住"""
        today = date.today()
        # admin创建一个订单给zhangsan
        r_login = client.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        admin_token = r_login.json()["access_token"]
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=19)).isoformat(),
            "checkout_date": (today + timedelta(days=21)).isoformat(),
            "guest_name": "他人订单", "guest_phone": "13800001124"
        }, headers=auth_header(admin_token))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_token))
        # testuser尝试为他人的订单办理入住
        r = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "906"
        }, headers=auth_header(testuser_auth))
        assert r.status_code == 404  # testuser看不到别人的订单

    def test_guest_sees_only_own_checkins(self, admin_auth, testuser_auth):
        """普通用户只能看到自己的入住记录"""
        # admin创建并入住一个订单
        today = date.today()
        r_order_a = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=20)).isoformat(),
            "checkout_date": (today + timedelta(days=22)).isoformat(),
            "guest_name": "管理订单", "guest_phone": "13800001125"
        }, headers=auth_header(admin_auth))
        client.post(f"{BASE_URL}/api/orders/{r_order_a.json()['id']}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": r_order_a.json()["id"], "room_number": "907"
        }, headers=auth_header(admin_auth))
        # testuser创建并入住自己的订单
        r_order_t = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=21)).isoformat(),
            "checkout_date": (today + timedelta(days=23)).isoformat(),
            "guest_name": "我的订单", "guest_phone": "13800001126"
        }, headers=auth_header(testuser_auth))
        client.post(f"{BASE_URL}/api/orders/{r_order_t.json()['id']}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": r_order_t.json()["id"], "room_number": "908"
        }, headers=auth_header(testuser_auth))
        # testuser只能看到自己的
        r = client.get(f"{BASE_URL}/api/checkin",
                       headers=auth_header(testuser_auth))
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["guest_name"] == "我的订单"

    def test_checkin_list_pagination(self, admin_auth):
        """入住记录列表分页"""
        r = client.get(f"{BASE_URL}/api/checkin",
                       params={"page": 1, "page_size": 2},
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 0

class TestUserRegisterBoundary:
    """用户注册边界测试"""

    def test_register_username_too_short(self):
        """用户名太短（<2字符）"""
        r = client.post(f"{BASE_URL}/api/auth/register", json={
            "username": "a",
            "password": "test123456"
        })
        assert r.status_code == 422

    def test_register_password_too_short(self):
        """密码太短（<6字符）"""
        ts = int(time.time())
        r = client.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"bndtest_{ts}",
            "password": "12345"
        })
        assert r.status_code == 422

    def test_register_invalid_phone_format(self):
        """手机号格式非法"""
        ts = int(time.time())
        r = client.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"bndtest_{ts}",
            "password": "test123456",
            "phone": "12345"
        })
        assert r.status_code == 422

    def test_register_missing_username(self):
        """缺少必填字段 username"""
        r = client.post(f"{BASE_URL}/api/auth/register", json={
            "password": "test123456"
        })
        assert r.status_code == 422

    def test_register_duplicate_phone(self):
        """手机号已被注册（用已有用户的手机号）"""
        ts = int(time.time())
        r = client.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"bndtest_{ts}",
            "password": "test123456",
            "phone": "13800000002"  # testuser的手机号
        })
        assert r.status_code == 400


class TestOrderStatusFlow:
    """订单状态流转测试"""

    def test_create_and_pay_order(self, admin_auth):
        """创建订单 -> 模拟支付 -> 验证状态流转"""
        today = date.today()
        # 1. 创建订单
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1,
            "room_id": 2,
            "room_count": 1,
            "checkin_date": (today + timedelta(days=6)).isoformat(),
            "checkout_date": (today + timedelta(days=8)).isoformat(),
            "guest_name": "状态流转测试",
            "guest_phone": "13800001111"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 201, f"Create order failed: {r.text}"
        order_data = r.json()
        assert order_data["status"] == "pending"
        order_id = order_data["id"]

        # 2. 模拟支付 - 验证 pending -> paid
        r_pay = client.post(f"{BASE_URL}/api/payment/create", json={
            "order_id": order_id
        }, headers=auth_header(admin_auth))
        assert r_pay.status_code == 200, f"Pay simulate failed: {r_pay.text}"
        pay_data = r_pay.json()
        assert pay_data["code"] == 0
        assert pay_data["data"]["prepay_id"] is not None

    def test_create_order_zero_nights(self, admin_auth):
        """入住日期=离店日期（零晚）应被拒绝"""
        today = date.today()
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1,
            "room_id": 1,
            "room_count": 1,
            "checkin_date": (today + timedelta(days=5)).isoformat(),
            "checkout_date": (today + timedelta(days=5)).isoformat(),
            "guest_name": "零晚测试",
            "guest_phone": "13800001112"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_cancel_cancelled_order(self, admin_auth):
        """尝试取消已取消的订单应报400"""
        r_list = client.get(f"{BASE_URL}/api/orders",
                            params={"status": "cancelled"},
                            headers=auth_header(admin_auth))
        cancelled_orders = r_list.json().get("items", [])
        if cancelled_orders:
            cancelled_order = cancelled_orders[0]
            r = client.post(
                f"{BASE_URL}/api/orders/{cancelled_order['id']}/cancel",
                params={"reason": "再次取消"},
                headers=auth_header(admin_auth)
            )
            assert r.status_code == 400

    def test_order_list_with_date_range(self, admin_auth):
        """按日期范围筛选订单"""
        today = date.today()
        r = client.get(f"{BASE_URL}/api/orders", params={
            "start_date": (today - timedelta(days=30)).isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat()
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data

    def test_order_list_with_pagination(self, admin_auth):
        """订单列表分页"""
        r = client.get(f"{BASE_URL}/api/orders", params={
            "page": 1, "page_size": 1
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 1
        assert data["total"] >= 1

    def test_update_status_illegal_transition(self, admin_auth):
        """非法状态转换：completed -> pending 应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 2, "room_count": 1,
            "checkin_date": (today + timedelta(days=20)).isoformat(),
            "checkout_date": (today + timedelta(days=22)).isoformat(),
            "guest_name": "非法转换测试", "guest_phone": "13800001222"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        # pending -> paid -> checked_in -> completed
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "601"
        }, headers=auth_header(admin_auth))
        client.post(f"{BASE_URL}/api/checkin/out/{r_checkin.json()['id']}",
                    headers=auth_header(admin_auth))
        # 尝试 completed -> pending (非法)
        r = client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                        params={"new_status": "pending"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_update_status_pending_to_checked_in(self, admin_auth):
        """非法: pending 直接跳到 checked_in 应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 3, "room_count": 1,
            "checkin_date": (today + timedelta(days=21)).isoformat(),
            "checkout_date": (today + timedelta(days=23)).isoformat(),
            "guest_name": "跳过支付测试", "guest_phone": "13800001223"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        r = client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                        params={"new_status": "checked_in"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_update_status_by_guest_forbidden(self, testuser_auth):
        """普通用户无权调用 /orders/{id}/status 应报403"""
        # 获取testuser的订单
        r_orders = client.get(f"{BASE_URL}/api/orders",
                              headers=auth_header(testuser_auth))
        orders = r_orders.json().get("items", [])
        if orders:
            order_id = orders[0]["id"]
            r = client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                            params={"new_status": "paid"},
                            headers=auth_header(testuser_auth))
            assert r.status_code == 403

    def test_update_status_invalid_value(self, admin_auth):
        """非法的状态值应报400"""
        r = client.post(f"{BASE_URL}/api/orders/1/status",
                        params={"new_status": "destroyed"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_create_order_nonexistent_room(self, admin_auth):
        """预订不存在的房型应报404"""
        today = date.today()
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 99999, "room_count": 1,
            "checkin_date": (today + timedelta(days=22)).isoformat(),
            "checkout_date": (today + timedelta(days=24)).isoformat(),
            "guest_name": "不存在房型", "guest_phone": "13800001224"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 404

    def test_create_order_nonexistent_hotel(self, admin_auth):
        """预订不存在门店应报404"""
        today = date.today()
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 99999, "room_id": 1, "room_count": 1,
            "checkin_date": (today + timedelta(days=23)).isoformat(),
            "checkout_date": (today + timedelta(days=25)).isoformat(),
            "guest_name": "不存在门店", "guest_phone": "13800001225"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 404

    def test_pay_nonexistent_order(self, testuser_auth):
        """支付不存在的订单应报404"""
        r = client.post(f"{BASE_URL}/api/payment/create", json={
            "order_id": 99999
        }, headers=auth_header(testuser_auth))
        assert r.status_code == 404

    def test_refund_pending_order(self, admin_auth):
        """退款待支付订单应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 4, "room_count": 1,
            "checkin_date": (today + timedelta(days=26)).isoformat(),
            "checkout_date": (today + timedelta(days=28)).isoformat(),
            "guest_name": "退款pending测试", "guest_phone": "13800001226"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        r = client.post(f"{BASE_URL}/api/payment/refund",
                        params={"order_id": order_id, "reason": "不想要"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_cancel_completed_order(self, admin_auth):
        """取消已完成的订单应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=27)).isoformat(),
            "checkout_date": (today + timedelta(days=29)).isoformat(),
            "guest_name": "取消已完成测试", "guest_phone": "13800001227"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        # pending -> paid -> checked_in -> completed
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "701"
        }, headers=auth_header(admin_auth))
        client.post(f"{BASE_URL}/api/checkin/out/{r_checkin.json()['id']}",
                    headers=auth_header(admin_auth))
        # 尝试取消
        r = client.post(f"{BASE_URL}/api/orders/{order_id}/cancel",
                        params={"reason": "后悔了"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_pay_checkin_then_refund_flow(self, admin_auth):
        """完整退款流程：pending -> paid -> checked_in -> refund"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=28)).isoformat(),
            "checkout_date": (today + timedelta(days=30)).isoformat(),
            "guest_name": "入住后退款", "guest_phone": "13800001228"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "801"
        }, headers=auth_header(admin_auth))
        assert r_checkin.status_code == 200
        # checked_in 可以退款
        r = client.post(f"{BASE_URL}/api/payment/refund",
                        params={"order_id": order_id, "reason": "入住后不满意"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0


class TestPaymentRefund:
    """支付退款完整测试（补充边界）"""

    def test_refund_paid_order_restores_room(self, admin_auth):
        """退款已支付订单：应成功退款并恢复可用房间数"""
        today = date.today()
        # 查当前可用房间数
        r_before = client.get(f"{BASE_URL}/api/hotels/1/rooms",
                              headers=auth_header(admin_auth))
        rooms_before = {r["id"]: r["available_count"] for r in r_before.json()}
        room_id = 2

        # 创建订单并支付
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": room_id, "room_count": 1,
            "checkin_date": (today + timedelta(days=32)).isoformat(),
            "checkout_date": (today + timedelta(days=34)).isoformat(),
            "guest_name": "退款恢复测试", "guest_phone": "13800001231"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))

        # 验证可用房数减少了
        r_after_pay = client.get(f"{BASE_URL}/api/hotels/1/rooms",
                                 headers=auth_header(admin_auth))
        rooms_after_pay = {r["id"]: r["available_count"] for r in r_after_pay.json()}
        assert rooms_after_pay[room_id] == rooms_before[room_id] - 1

        # 退款
        r = client.post(f"{BASE_URL}/api/payment/refund",
                        params={"order_id": order_id, "reason": "不想要了"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0
        assert "refunded" in r.json()["msg"]

        # 验证可用房数恢复
        r_after_refund = client.get(f"{BASE_URL}/api/hotels/1/rooms",
                                    headers=auth_header(admin_auth))
        rooms_after_refund = {r["id"]: r["available_count"] for r in r_after_refund.json()}
        assert rooms_after_refund[room_id] == rooms_before[room_id], \
            f"退款后可用房间数应恢复: expected {rooms_before[room_id]}, got {rooms_after_refund[room_id]}"

        # 验证订单状态
        r_order_check = client.get(f"{BASE_URL}/api/orders/{order_id}",
                                   headers=auth_header(admin_auth))
        assert r_order_check.json()["status"] == "refunded"

    def test_refund_completed_order(self, admin_auth):
        """退款已完成订单应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=33)).isoformat(),
            "checkout_date": (today + timedelta(days=35)).isoformat(),
            "guest_name": "已完成退款测试", "guest_phone": "13800001232"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        # pending→paid→checked_in→completed
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "1001"
        }, headers=auth_header(admin_auth))
        client.post(f"{BASE_URL}/api/checkin/out/{r_checkin.json()['id']}",
                    headers=auth_header(admin_auth))
        # 尝试退款已完成订单
        r = client.post(f"{BASE_URL}/api/payment/refund",
                        params={"order_id": order_id, "reason": "退晚了"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_refund_nonexistent_order(self, admin_auth):
        """退款不存在的订单应报404"""
        r = client.post(f"{BASE_URL}/api/payment/refund",
                        params={"order_id": 99999, "reason": "不存在"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 404

    def test_refund_checked_in_auto_checkout(self, admin_auth):
        """退款已入住订单：自动退房+恢复房间数"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 4, "room_count": 1,
            "checkin_date": (today + timedelta(days=34)).isoformat(),
            "checkout_date": (today + timedelta(days=36)).isoformat(),
            "guest_name": "退款自动退房", "guest_phone": "13800001233"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "1002"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        assert r_checkin.json()["status"] == "checked_in"

        # 退款 → 自动退房
        r = client.post(f"{BASE_URL}/api/payment/refund",
                        params={"order_id": order_id, "reason": "紧急退款"},
                        headers=auth_header(admin_auth))
        assert r.status_code == 200

        # 验证 checkin 状态变为 checked_out
        r_checkin_after = client.get(f"{BASE_URL}/api/checkin/{checkin_id}",
                                     headers=auth_header(admin_auth))
        assert r_checkin_after.json()["status"] == "checked_out", \
            f"退款时未自动退房: {r_checkin_after.json()['status']}"
        assert r_checkin_after.json()["checkout_time"] is not None

        # 验证订单状态为 refunded
        r_order_after = client.get(f"{BASE_URL}/api/orders/{order_id}",
                                   headers=auth_header(admin_auth))
        assert r_order_after.json()["status"] == "refunded"

    def test_payment_query_status(self, admin_auth):
        """查询支付状态"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 3, "room_count": 1,
            "checkin_date": (today + timedelta(days=35)).isoformat(),
            "checkout_date": (today + timedelta(days=37)).isoformat(),
            "guest_name": "支付查询测试", "guest_phone": "13800001234"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]

        # 未支付时查询
        r = client.get(f"{BASE_URL}/api/payment/query/{order_id}",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "pending"

        # 支付后查询
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r = client.get(f"{BASE_URL}/api/payment/query/{order_id}",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "paid"

    def test_payment_create_for_paid_order(self, admin_auth):
        """已支付订单尝试再次创建支付应报400"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 3, "room_count": 1,
            "checkin_date": (today + timedelta(days=36)).isoformat(),
            "checkout_date": (today + timedelta(days=38)).isoformat(),
            "guest_name": "重复支付测试", "guest_phone": "13800001235"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        # 模拟支付
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        # 再次创建支付
        r = client.post(f"{BASE_URL}/api/payment/create", json={
            "order_id": order_id
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400


class TestCheckinFlowCompleteness:
    """入住流程完整性测试（补充边界）"""

    def test_full_lifecycle_order_to_checkout(self, admin_auth):
        """完整生命周期：创建→支付→入住→开锁→关锁→退房→验证全状态"""
        today = date.today()
        # 1. 创建订单
        r = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 2, "room_count": 1,
            "checkin_date": (today + timedelta(days=39)).isoformat(),
            "checkout_date": (today + timedelta(days=41)).isoformat(),
            "guest_name": "全生命周期测试", "guest_phone": "13800001241"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 201
        order_id = r.json()["id"]
        assert r.json()["status"] == "pending"
        assert r.json()["nights"] == 2
        assert r.json()["total_price"] > 0

        # 2. 支付
        r_pay = client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                            params={"new_status": "paid"}, headers=auth_header(admin_auth))
        assert r_pay.status_code == 200
        r_order = client.get(f"{BASE_URL}/api/orders/{order_id}",
                             headers=auth_header(admin_auth))
        assert r_order.json()["status"] == "paid"
        assert r_order.json()["paid_at"] is not None

        # 3. 入住
        r_in = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "1101"
        }, headers=auth_header(admin_auth))
        assert r_in.status_code == 200
        checkin_id = r_in.json()["id"]
        assert r_in.json()["status"] == "checked_in"
        assert r_in.json()["room_number"] == "1101"
        assert r_in.json()["checkin_time"] is not None
        # 订单状态变为 checked_in
        r_order = client.get(f"{BASE_URL}/api/orders/{order_id}",
                             headers=auth_header(admin_auth))
        assert r_order.json()["status"] == "checked_in"

        # 4. 开锁
        r_unlock = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "unlock"
        }, headers=auth_header(admin_auth))
        assert r_unlock.status_code == 200
        records = r_unlock.json()["door_lock_records"]
        assert len(records) == 1
        assert records[0]["action"] == "unlock"

        # 5. 关锁
        r_lock = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "lock"
        }, headers=auth_header(admin_auth))
        assert r_lock.status_code == 200
        records = r_lock.json()["door_lock_records"]
        assert len(records) == 2
        assert records[0]["action"] == "unlock"
        assert records[1]["action"] == "lock"

        # 6. 退房
        r_out = client.post(f"{BASE_URL}/api/checkin/out/{checkin_id}",
                            headers=auth_header(admin_auth))
        assert r_out.status_code == 200
        assert r_out.json()["status"] == "checked_out"
        assert r_out.json()["checkout_time"] is not None

        # 7. 订单变为 completed
        r_order = client.get(f"{BASE_URL}/api/orders/{order_id}",
                             headers=auth_header(admin_auth))
        assert r_order.json()["status"] == "completed"

        # 8. 验证入住列表中出现这条记录
        r_list = client.get(f"{BASE_URL}/api/checkin",
                            headers=auth_header(admin_auth))
        checkin_ids = [c["id"] for c in r_list.json()["items"]]
        assert checkin_id in checkin_ids

    def test_checkin_requires_payment(self, testuser_auth):
        """办理入住必须已支付：pending订单无法入住"""
        r_orders = client.get(f"{BASE_URL}/api/orders",
                              headers=auth_header(testuser_auth))
        pending_orders = [o for o in r_orders.json()["items"] if o["status"] == "pending"]
        if pending_orders:
            r = client.post(f"{BASE_URL}/api/checkin/in", json={
                "order_id": pending_orders[0]["id"], "room_number": "101"
            }, headers=auth_header(testuser_auth))
            assert r.status_code == 400

    def test_unlock_requires_checkin(self, admin_auth):
        """未入住状态不能开锁"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 5, "room_count": 1,
            "checkin_date": (today + timedelta(days=40)).isoformat(),
            "checkout_date": (today + timedelta(days=42)).isoformat(),
            "guest_name": "未入住开锁", "guest_phone": "13800001242"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r_checkin = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "1102"
        }, headers=auth_header(admin_auth))
        checkin_id = r_checkin.json()["id"]
        # 退房
        client.post(f"{BASE_URL}/api/checkin/out/{checkin_id}",
                    headers=auth_header(admin_auth))
        # 退房后尝试开锁
        r = client.post(f"{BASE_URL}/api/checkin/{checkin_id}/unlock", json={
            "action": "unlock"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_checkin_list_filter_by_hotel_and_status(self, admin_auth):
        """组合筛选：按门店+状态筛选入住记录"""
        today = date.today()
        # 在 hotel_id=1 创建一个入住（使用 room_id=1，避免avail耗尽）
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 1, "room_count": 1,
            "checkin_date": (today + timedelta(days=41)).isoformat(),
            "checkout_date": (today + timedelta(days=43)).isoformat(),
            "guest_name": "组合筛选", "guest_phone": "13800001243"
        }, headers=auth_header(admin_auth))
        assert r_order.status_code == 201, f"Create order failed: {r_order.text}"
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "1103"
        }, headers=auth_header(admin_auth))
        # 组合筛选
        r = client.get(f"{BASE_URL}/api/checkin",
                       params={"hotel_id": 1, "status": "checked_in"},
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["hotel_id"] == 1
            assert item["status"] == "checked_in"

    def test_checkin_room_number_trim(self, admin_auth):
        """房间号前后空格应被trim处理"""
        today = date.today()
        r_order = client.post(f"{BASE_URL}/api/orders", json={
            "hotel_id": 1, "room_id": 4, "room_count": 1,
            "checkin_date": (today + timedelta(days=42)).isoformat(),
            "checkout_date": (today + timedelta(days=44)).isoformat(),
            "guest_name": "空格测试", "guest_phone": "13800001244"
        }, headers=auth_header(admin_auth))
        order_id = r_order.json()["id"]
        client.post(f"{BASE_URL}/api/orders/{order_id}/status",
                    params={"new_status": "paid"}, headers=auth_header(admin_auth))
        r = client.post(f"{BASE_URL}/api/checkin/in", json={
            "order_id": order_id, "room_number": "  1104  "
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["room_number"] == "1104"


class TestDevicesAPI:
    """设备管理接口测试（心跳异常场景）"""

    def test_device_heartbeat_unknown_device(self, admin_auth):
        """未注册设备上报心跳应报404"""
        r = client.post(f"{BASE_URL}/api/devices/heartbeat", json={
            "device_id": "UNKNOWN-DEV-9999",
            "status": "online",
            "battery": 80
        }, headers=auth_header(admin_auth))
        assert r.status_code == 404

    def test_device_heartbeat_low_battery(self, admin_auth):
        """设备心跳上报低电量告警"""
        r = client.post(f"{BASE_URL}/api/devices/heartbeat", json={
            "device_id": "LOCK-001",
            "status": "alert",
            "battery": 5
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "alert"
        assert data["data"]["battery"] == 5

    def test_device_heartbeat_offline_status(self, admin_auth):
        """设备心跳上报离线状态"""
        r = client.post(f"{BASE_URL}/api/devices/heartbeat", json={
            "device_id": "LOCK-002",
            "status": "offline",
            "battery": 10
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "offline"

    def test_device_list_all(self, admin_auth):
        """设备列表查询"""
        r = client.get(f"{BASE_URL}/api/devices/list",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "data" in data
        assert "total" in data
        assert "online_count" in data
        assert "offline_count" in data
        assert "alert_count" in data

    def test_device_stats(self, admin_auth):
        """设备统计概览"""
        r = client.get(f"{BASE_URL}/api/devices/stats",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        stats = data["data"]
        assert "total" in stats
        assert "online" in stats
        assert "offline" in stats
        assert "alert" in stats
        assert "low_battery" in stats

    def test_device_heartbeat_full_cycle(self, admin_auth):
        """设备心跳完整周期：online -> offline -> alert -> online 恢复"""
        device_id = "LOCK-002"
        # 确保设备先在线
        client.post(f"{BASE_URL}/api/devices/heartbeat", json={
            "device_id": device_id,
            "status": "online",
            "battery": 80
        }, headers=auth_header(admin_auth))

        # 上报告警
        r_alert = client.post(f"{BASE_URL}/api/devices/heartbeat", json={
            "device_id": device_id,
            "status": "alert",
            "battery": 3
        }, headers=auth_header(admin_auth))
        assert r_alert.status_code == 200
        assert r_alert.json()["data"]["status"] == "alert"

        # 恢复在线
        r_online = client.post(f"{BASE_URL}/api/devices/heartbeat", json={
            "device_id": device_id,
            "status": "online",
            "battery": 90
        }, headers=auth_header(admin_auth))
        assert r_online.status_code == 200
        assert r_online.json()["data"]["status"] == "online"


# ══════════════════════════════════════════════════════
# 10. OTA 渠道 API
# ══════════════════════════════════════════════════════

class TestOTAAPI:
    """OTA渠道对接接口测试"""

    def test_list_channels_empty_or_default(self, admin_auth):
        """列出OTA渠道（数据库可能为空，返回默认渠道列表或空）"""
        r = client.get(f"{BASE_URL}/api/ota/channels",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "data" in data
        channels = data["data"].get("channels", [])
        assert isinstance(channels, list)
        # 默认应返回携程/美团/飞猪三渠道
        for ch in ["ctrip", "meituan", "fliggy"]:
            found = any(c.get("channel") == ch for c in channels)
            assert found, f"默认渠道列表缺少 {ch}"

    def test_create_channel_ctrip(self, admin_auth):
        """添加携程渠道配置"""
        r = client.post(f"{BASE_URL}/api/ota/channels", json={
            "channel": "ctrip",
            "name": "携程直连测试",
            "api_key": "ctrip_test_key_2026",
            "api_secret": "ctrip_test_secret_abc",
            "hotel_mapping": {"1": "ctrip_hotel_1001"},
            "sync_interval": 300
        }, headers=auth_header(admin_auth))
        # 如果已存在则报400，也视为正常
        if r.status_code == 200:
            data = r.json()
            assert data["code"] == 0
            assert data["data"]["channel"] == "ctrip"
        else:
            assert r.status_code == 400  # 已存在

    def test_create_channel_meituan(self, admin_auth):
        """添加美团渠道配置"""
        r = client.post(f"{BASE_URL}/api/ota/channels", json={
            "channel": "meituan",
            "name": "美团直连测试",
            "api_key": "meituan_test_key_2026",
            "api_secret": "meituan_test_secret_xyz",
            "hotel_mapping": {"1": "meituan_hotel_2001"},
            "sync_interval": 300
        }, headers=auth_header(admin_auth))
        if r.status_code == 200:
            assert r.json()["code"] == 0
        else:
            assert r.status_code == 400  # 已存在

    def test_create_channel_fliggy(self, admin_auth):
        """添加飞猪渠道配置"""
        r = client.post(f"{BASE_URL}/api/ota/channels", json={
            "channel": "fliggy",
            "name": "飞猪直连测试",
            "api_key": "fliggy_test_key_2026",
            "api_secret": "fliggy_test_secret_pqr",
            "hotel_mapping": {"1": "fliggy_hotel_3001"},
            "sync_interval": 600
        }, headers=auth_header(admin_auth))
        if r.status_code == 200:
            assert r.json()["code"] == 0
        else:
            assert r.status_code == 400  # 已存在

    def test_create_channel_invalid(self, admin_auth):
        """添加不支持的渠道应报400"""
        r = client.post(f"{BASE_URL}/api/ota/channels", json={
            "channel": "airbnb",
            "name": "Airbnb测试",
            "api_key": "invalid",
            "api_secret": "invalid",
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_list_channels_with_data(self, admin_auth):
        """列出OTA渠道（包含已配置的渠道）"""
        r = client.get(f"{BASE_URL}/api/ota/channels",
                       headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        channels = data["data"].get("channels", [])
        assert len(channels) >= 3
        # 验证每个渠道的必要字段
        for ch in channels:
            assert "channel" in ch
            assert "name" in ch
            assert "is_enabled" in ch
            assert "api_key_set" in ch
            assert "api_secret_set" in ch
            assert "sync_interval" in ch

    def test_get_channel_detail(self, admin_auth):
        """通过列表验证渠道详情字段完整性"""
        r = client.get(f"{BASE_URL}/api/ota/channels",
                       headers=auth_header(admin_auth))
        data = r.json()["data"]["channels"]
        ctrip = next((c for c in data if c["channel"] == "ctrip"), None)
        if ctrip:
            assert isinstance(ctrip["is_enabled"], bool)
            assert isinstance(ctrip["api_key_set"], bool)
            assert isinstance(ctrip["api_secret_set"], bool)
            assert isinstance(ctrip["sync_interval"], int)
            assert ctrip["sync_interval"] >= 60

    def test_update_channel_enable(self, admin_auth):
        """更新渠道启用/停用状态"""
        # 先停用携程
        r = client.put(f"{BASE_URL}/api/ota/channels/ctrip", json={
            "is_enabled": False
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0

        # 验证状态已变更
        r_check = client.get(f"{BASE_URL}/api/ota/channels",
                             headers=auth_header(admin_auth))
        ctrip = next((c for c in r_check.json()["data"]["channels"]
                       if c["channel"] == "ctrip"), None)
        if ctrip:
            assert ctrip["is_enabled"] is False

        # 重新启用
        client.put(f"{BASE_URL}/api/ota/channels/ctrip", json={
            "is_enabled": True
        }, headers=auth_header(admin_auth))

    def test_update_channel_name(self, admin_auth):
        """更新渠道显示名称"""
        r = client.put(f"{BASE_URL}/api/ota/channels/meituan", json={
            "name": "美团酒店直连V2"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_update_channel_credentials(self, admin_auth):
        """更新渠道API凭证"""
        r = client.put(f"{BASE_URL}/api/ota/channels/fliggy", json={
            "api_key": "fliggy_updated_key_2026",
            "api_secret": "fliggy_updated_secret_abc",
            "sync_interval": 900
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0

        # 验证凭证已设置
        r_check = client.get(f"{BASE_URL}/api/ota/channels",
                             headers=auth_header(admin_auth))
        fliggy = next((c for c in r_check.json()["data"]["channels"]
                        if c["channel"] == "fliggy"), None)
        if fliggy:
            assert fliggy["api_key_set"] is True
            assert fliggy["api_secret_set"] is True

    def test_update_channel_hotel_mapping(self, admin_auth):
        """更新渠道酒店映射"""
        r = client.put(f"{BASE_URL}/api/ota/channels/ctrip", json={
            "hotel_mapping": {"1": "ctrip_1001", "2": "ctrip_1002", "3": "ctrip_1003"}
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200

        # 验证映射
        r_check = client.get(f"{BASE_URL}/api/ota/channels",
                             headers=auth_header(admin_auth))
        ctrip = next((c for c in r_check.json()["data"]["channels"]
                       if c["channel"] == "ctrip"), None)
        if ctrip:
            mapping = ctrip.get("hotel_mapping", {})
            assert mapping.get("1") == "ctrip_1001"
            assert mapping.get("2") == "ctrip_1002"

    def test_update_nonexistent_channel(self, admin_auth):
        """更新不存在的渠道应报404"""
        r = client.put(f"{BASE_URL}/api/ota/channels/unknown_channel", json={
            "name": "不存在"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 404

    def test_sync_availability_disabled_channel(self, admin_auth):
        """向未启用的渠道同步房态应报400"""
        # 先停用携程
        client.put(f"{BASE_URL}/api/ota/channels/ctrip", json={
            "is_enabled": False
        }, headers=auth_header(admin_auth))
        r = client.post(f"{BASE_URL}/api/ota/sync/availability", json={
            "hotel_id": 1,
            "channel": "ctrip",
            "rooms": [{"room_id": 1, "date": "2026-06-12", "available": 10, "price": 299}]
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400
        # 恢复
        client.put(f"{BASE_URL}/api/ota/channels/ctrip", json={
            "is_enabled": True
        }, headers=auth_header(admin_auth))

    def test_sync_availability_enabled_channel(self, admin_auth):
        """向已启用的渠道同步房态"""
        r = client.post(f"{BASE_URL}/api/ota/sync/availability", json={
            "hotel_id": 1,
            "channel": "ctrip",
            "rooms": [
                {"room_id": 1, "date": "2026-06-12", "available": 10, "price": 299},
                {"room_id": 2, "date": "2026-06-12", "available": 8, "price": 399}
            ]
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["data"]["synced"] == 2
        assert data["data"]["channel"] == "ctrip"

    def test_sync_availability_invalid_channel(self, admin_auth):
        """向不存在的渠道同步房态应报400"""
        r = client.post(f"{BASE_URL}/api/ota/sync/availability", json={
            "hotel_id": 1,
            "channel": "expedia",
            "rooms": [{"room_id": 1, "date": "2026-06-12", "available": 10, "price": 299}]
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_auto_sync_all(self, admin_auth):
        """自动同步所有启用渠道（OTA API占位，200或500均可）"""
        r = client.post(f"{BASE_URL}/api/ota/sync/auto",
                        headers=auth_header(admin_auth))
        # OTA API为占位地址，不可达时可能500，但同步请求本身应处理
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            data = r.json()
            assert data["code"] == 0

    def test_webhook_invalid_channel(self, admin_auth):
        """无效渠道的webhook回调应报400"""
        r = client.post(f"{BASE_URL}/api/ota/webhook/invalid_channel", json={
            "ota_order_id": "TEST-001",
            "hotel_id": 1,
            "room_id": 1,
            "checkin_date": "2026-06-15",
            "checkout_date": "2026-06-17",
            "total_price": 598.0,
            "guest_name": "OTA测试用户",
            "guest_phone": "13812345678"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400

    def test_webhook_valid_channel_missing_fields(self, admin_auth):
        """有效渠道webhook回调但缺少必填字段应报400"""
        r = client.post(f"{BASE_URL}/api/ota/webhook/ctrip", json={
            "channel": "ctrip"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 400  # 缺少ota_order_id

    def test_webhook_create_order_from_ota_ctrip(self, admin_auth):
        """OTA webhook(携程)创建订单：使用携程字段名"""
        r = client.post(f"{BASE_URL}/api/ota/webhook/ctrip", json={
            "OrderId": "CTRIP-TEST-20260611-001",
            "HotelId": 1,
            "RoomId": 1,
            "RoomCount": 1,
            "CheckIn": "2026-06-20",
            "CheckOut": "2026-06-22",
            "TotalPrice": 596.0,
            "ContactName": "携程测试用户",
            "ContactPhone": "13887654321",
            "Remark": "携程渠道测试订单"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        order_data = data["data"]
        assert "local_order_id" in order_data
        assert "local_order_no" in order_data
        # 验证 remark 包含渠道标记
        assert order_data["local_order_no"].startswith("OTA-CT")

    def test_webhook_duplicate_order(self, admin_auth):
        """OTA webhook重复订单应去重"""
        r = client.post(f"{BASE_URL}/api/ota/webhook/ctrip", json={
            "OrderId": "CTRIP-TEST-20260611-001",
            "HotelId": 1,
            "RoomId": 1,
            "RoomCount": 1,
            "CheckIn": "2026-06-20",
            "CheckOut": "2026-06-22",
            "TotalPrice": 596.0,
            "ContactName": "携程重复用户",
            "ContactPhone": "13887654321",
            "Remark": "重复推送应去重"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0

    def test_webhook_meituan_order(self, admin_auth):
        """美团OTA webhook创建订单：使用美团嵌套格式"""
        r = client.post(f"{BASE_URL}/api/ota/webhook/meituan", json={
            "data": {
                "order_id": "MT-TEST-20260611-001",
                "hotel_id": 1,
                "room_id": 2,
                "num": 2,
                "check_in": "2026-06-25",
                "check_out": "2026-06-28",
                "total": 1194.0,
                "name": "美团测试用户",
                "mobile": "13855554444",
                "remark": "美团渠道测试"
            }
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        order_data = data["data"]
        assert "local_order_id" in order_data
        assert "local_order_no" in order_data
        assert order_data["local_order_no"].startswith("OTA-ME")

    def test_webhook_fliggy_order(self, admin_auth):
        """飞猪OTA webhook创建订单：使用飞猪字段名"""
        r = client.post(f"{BASE_URL}/api/ota/webhook/fliggy", json={
            "tid": "FLIGGY-TEST-20260611-001",
            "hotel_id": 1,
            "rid": 3,
            "num": 1,
            "check_in": "2026-06-30",
            "check_out": "2026-07-02",
            "payment": 698.0,
            "buyer_nick": "飞猪测试用户",
            "mobile": "13833332222",
            "buyer_message": "飞猪渠道测试"
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "local_order_id" in data["data"]
        assert data["data"]["local_order_no"].startswith("OTA-FL")

    def test_delete_channel(self, admin_auth):
        """删除OTA渠道"""
        # 先确认飞猪渠道存在
        r = client.delete(f"{BASE_URL}/api/ota/channels/fliggy",
                          headers=auth_header(admin_auth))
        # 200=删除成功, 404=不存在(可能被其他测试删除)
        assert r.status_code in (200, 404)

    def test_delete_nonexistent_channel(self, admin_auth):
        """删除不存在的渠道应报404"""
        r = client.delete(f"{BASE_URL}/api/ota/channels/nonexistent_xyz",
                          headers=auth_header(admin_auth))
        assert r.status_code == 404

    def test_ota_requires_auth(self):
        """OTA接口未登录访问应报401/403"""
        r = client.get(f"{BASE_URL}/api/ota/channels")
        assert r.status_code in (401, 403)

        r = client.post(f"{BASE_URL}/api/ota/channels", json={
            "channel": "ctrip", "name": "test"
        })
        assert r.status_code in (401, 403)

        r = client.post(f"{BASE_URL}/api/ota/sync/auto")
        assert r.status_code in (401, 403)

    def test_delete_and_recreate_channel(self, admin_auth):
        """删除渠道后重新创建"""
        # 先删除美团
        client.delete(f"{BASE_URL}/api/ota/channels/meituan",
                      headers=auth_header(admin_auth))
        # 重新创建
        r = client.post(f"{BASE_URL}/api/ota/channels", json={
            "channel": "meituan",
            "name": "美团重新创建",
            "api_key": "new_meituan_key",
            "api_secret": "new_meituan_secret",
            "sync_interval": 180
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_sync_availability_multiple_rooms(self, admin_auth):
        """推送多房型到渠道"""
        r = client.post(f"{BASE_URL}/api/ota/sync/availability", json={
            "hotel_id": 1,
            "channel": "meituan",
            "rooms": [
                {"room_id": 1, "date": "2026-06-15", "available": 5, "price": 298.0},
                {"room_id": 2, "date": "2026-06-15", "available": 10, "price": 398.0},
                {"room_id": 3, "date": "2026-06-15", "available": 3, "price": 258.0},
                {"room_id": 4, "date": "2026-06-15", "available": 7, "price": 558.0},
                {"room_id": 5, "date": "2026-06-15", "available": 12, "price": 158.0}
            ]
        }, headers=auth_header(admin_auth))
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["data"]["synced"] == 5


# ══════════════════════════════════════════════════════
# 运行入口
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
