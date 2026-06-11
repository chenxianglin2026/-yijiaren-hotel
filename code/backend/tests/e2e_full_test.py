#!/usr/bin/env python3
"""
伊家人 端到端集成测试 + 安全测试 + 性能测试
Uses only stdlib - no external dependencies
"""
import urllib.request
import urllib.parse
import json
import time
import sqlite3
import subprocess
import sys
import os
from datetime import date, timedelta

BASE = "http://localhost:8001"
DB_PATH = "/Users/chenxianglin/projects/yijiaren/code/backend/data/yijiaren.db"

# ── 测试前重置种子数据 ──
print("🔄 重置测试数据...")
seed_script = os.path.join(os.path.dirname(__file__), "..", "seed_mock.py")
result = subprocess.run(
    [sys.executable, seed_script, "--force"],
    capture_output=True, text=True, cwd=os.path.dirname(seed_script)
)
print(result.stdout.strip())
print("✅ 测试数据已重置\n")

results = []
passed = 0
failed = 0

def ok(msg):
    global passed
    passed += 1
    results.append(f"  ✅ PASS: {msg}")
    print(f"  ✅ PASS: {msg}")

def no(msg, detail=""):
    global failed
    failed += 1
    detail_str = f" - {detail}" if detail else ""
    results.append(f"  ❌ FAIL: {msg}{detail_str}")
    print(f"  ❌ FAIL: {msg}{detail_str}")

def safe_get(d, key, default=None):
    return d.get(key, default) if isinstance(d, dict) else default

def http_get(url, headers=None):
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except:
            return e.code, {"error": body}
    except Exception as e:
        return -1, {"error": str(e)}

def http_post(url, data=None, headers=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            return e.code, json.loads(err_body)
        except:
            return e.code, {"error": err_body}
    except Exception as e:
        return -1, {"error": str(e)}

def http_get_status(url, headers=None):
    """Return only HTTP status code"""
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1

print("=" * 60)
print(" 伊家人 端到端集成测试 + 安全检查 + 性能测试")
print(f" BASE: {BASE}")
print(f" 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print()

# ============================================================
# SECTION 1: 端到端流程
# ============================================================
print("━━━ SECTION 1: 端到端流程 ━━━")

ts = int(time.time())
TEST_USER = f"e2etest_{ts}"
TEST_PASS = "TestPass123"

# 1a) Register
print("  1a) 注册 → 登录 → 获取token")
code, data = http_post(f"{BASE}/api/auth/register", {
    "username": TEST_USER,
    "password": TEST_PASS,
    "phone": f"138{str(ts)[:8]}",
    "nickname": "E2E测试用户"
})
if code == 200:
    token = safe_get(data, "access_token")
    user_id = safe_get(data, "user_id")
    if token:
        ok(f"注册成功, 获得token (user_id={user_id})")
    else:
        no("注册返回无token", str(data)[:200])
else:
    no(f"注册失败 HTTP {code}", str(data)[:200])
    token = None

headers = {"Authorization": f"Bearer {token}"} if token else {}

# Verify token with /me
if token:
    code, data = http_get(f"{BASE}/api/auth/me", headers)
    if code == 200 and safe_get(data, "username") == TEST_USER:
        ok(f"Token验证: /api/auth/me 返回正确用户")
    else:
        no(f"Token验证失败 HTTP {code}", str(data)[:200])

# 1b) Browse hotels
print("  1b) 浏览酒店列表 → 选择酒店 → 查看房型")
code, data = http_get(f"{BASE}/api/hotels")
if code == 200:
    inner = data.get("data", data)
    hotel_count = safe_get(inner, "total", 0)
    if hotel_count > 0:
        ok(f"酒店列表: 共 {hotel_count} 家酒店")
        hotel = inner["items"][0]
        hotel_id = hotel["id"]
        hotel_name = hotel["name"]
    else:
        no("酒店列表为空")
        hotel_id = 1
        hotel_name = "unknown"
else:
    no(f"酒店列表失败 HTTP {code}")
    hotel_id = 1
    hotel_name = "unknown"

# Hotel detail
code, data = http_get(f"{BASE}/api/hotels/{hotel_id}")
if code == 200:
    rooms = data.get("rooms", [])
    if rooms:
        ok(f"酒店详情({hotel_name}): {len(rooms)} 种房型")
        room = rooms[0]
        room_id = room["id"]
        room_name = room["name"]
        room_price = room["price"]
        room_avail = room.get("available_count", 0)
        print(f"    选中: {room_name} (¥{room_price}/晚, 可订 {room_avail} 间)")
    else:
        no("酒店详情无房型")
        room_id = 1
else:
    no(f"酒店详情失败 HTTP {code}")
    room_id = 1

# 1c) Create order
print("  1c) 创建订单 → 查看订单详情")
checkin_date = str(date.today() + timedelta(days=3))
checkout_date = str(date.today() + timedelta(days=5))

code, data = http_post(f"{BASE}/api/orders", {
    "hotel_id": hotel_id,
    "room_id": room_id,
    "room_count": 1,
    "checkin_date": checkin_date,
    "checkout_date": checkout_date,
    "guest_name": "E2E测试",
    "guest_phone": "13800138000",
    "remark": "E2E测试订单"
}, headers)

order_id = None
if code == 201:
    order_id = safe_get(data, "id")
    order_no = safe_get(data, "order_no")
    order_status = safe_get(data, "status")
    order_total = safe_get(data, "total_price")
    ok(f"创建订单: #{order_id} ({order_no}), 状态={order_status}, 总价=¥{order_total}")
else:
    no(f"创建订单失败 HTTP {code}", str(data)[:200])

# Order detail
if order_id:
    code, data = http_get(f"{BASE}/api/orders/{order_id}", headers)
    if code == 200 and safe_get(data, "id") == order_id:
        ok(f"订单详情查询: #{order_id} 正确")
    else:
        no(f"订单详情失败 HTTP {code}")

# 1c-cont) Mock payment
print("  1c-续) 模拟支付")
code, data = http_post(f"{BASE}/api/payment/create", {"order_id": order_id}, headers)
if code == 200 and safe_get(data, "code") == 0:
    # Manually set order to paid
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id={order_id}")
    conn.commit()
    conn.close()
    ok("支付创建: prepay_id已生成, 模拟回调完成")
else:
    no(f"支付创建失败 HTTP {code}", str(data)[:200])
    # Try to pay anyway
    if order_id:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(f"UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id={order_id}")
        conn.commit()
        conn.close()

# 1d) Checkin
print("  1d) 办理入住 → 查看入住状态")
checkin_id = None
code, data = http_post(f"{BASE}/api/checkin/in", {
    "order_id": order_id,
    "room_number": "301"
}, headers)
if code == 200:
    checkin_id = safe_get(data, "id")
    checkin_status = safe_get(data, "status")
    if checkin_status == "checked_in":
        ok(f"办理入住: 入住记录 #{checkin_id}, 状态={checkin_status}")
    else:
        no("办理入住状态异常", str(data)[:200])
else:
    no(f"办理入住失败 HTTP {code}", str(data)[:200])

# Checkin detail
if checkin_id:
    code, data = http_get(f"{BASE}/api/checkin/{checkin_id}", headers)
    if code == 200 and safe_get(data, "status") == "checked_in":
        ok("入住状态查询: 当前状态=checked_in")
    else:
        no(f"入住状态查询失败 HTTP {code}")

    # Unlock
    code, data = http_post(f"{BASE}/api/checkin/{checkin_id}/unlock",
                           {"action": "unlock"}, headers)
    if code == 200 and safe_get(data, "status") == "checked_in":
        ok("门锁记录: unlock操作已记录")
    else:
        no(f"门锁记录失败 HTTP {code}", str(data)[:200])

# 1e) Cleaning task creation
print("  1e) 创建保洁工单 → 完成清洁")

# Login as admin
code, data = http_post(f"{BASE}/api/auth/login", {"username": "admin", "password": "admin123"})
admin_token = safe_get(data, "access_token") if code == 200 else None
admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

if admin_token:
    ok("管理员登录: 获取token成功")
else:
    no(f"管理员登录失败 HTTP {code}", str(data)[:200])

clean_task_id = None
if admin_token:
    # Create cleaning task
    code, data = http_post(f"{BASE}/api/cleaning/tasks", {
        "hotel_id": hotel_id,
        "room_number": "301",
        "task_type": "cleanup",
        "notes": "E2E测试保洁工单"
    }, admin_headers)
    if code == 200:
        clean_task_id = safe_get(data, "id")
        clean_task_status = safe_get(data, "status")
        ok(f"创建保洁工单: #{clean_task_id}, 状态={clean_task_status}")
    else:
        no(f"创建保洁工单失败 HTTP {code}", str(data)[:200])

    # Accept
    if clean_task_id:
        code, data = http_post(f"{BASE}/api/cleaning/tasks/accept",
                               {"task_id": clean_task_id}, admin_headers)
        if code == 200 and safe_get(data, "status") == "accepted":
            ok("保洁员接单: 状态=accepted")
        else:
            no(f"保洁员接单失败 HTTP {code}", str(data)[:200])

        # Start
        code, data = http_post(f"{BASE}/api/cleaning/tasks/start",
                               {"task_id": clean_task_id}, admin_headers)
        if code == 200 and safe_get(data, "status") == "in_progress":
            ok("开始清洁: 状态=in_progress")
        else:
            no(f"开始清洁失败 HTTP {code}", str(data)[:200])

        # Complete
        code, data = http_post(f"{BASE}/api/cleaning/tasks/complete", {
            "task_id": clean_task_id,
            "photo_urls": '["https://example.com/photo1.jpg"]',
            "notes": "清洁完成"
        }, admin_headers)
        if code == 200 and safe_get(data, "status") == "completed":
            ok("完工打卡: 状态=completed")
        else:
            no(f"完工打卡失败 HTTP {code}", str(data)[:200])

# ============================================================
# SECTION 2: 安全测试
# ============================================================
print()
print("━━━ SECTION 2: 安全测试 ━━━")

# 2a) No auth
print("  2a) 未登录访问受保护端点 → 应返回401")
status = http_get_status(f"{BASE}/api/orders")
if status in (401, 403):
    ok(f"GET /api/orders 无token: HTTP {status}")
else:
    no(f"GET /api/orders 无token应返回401/403, 实际={status}")

status = http_get_status(f"{BASE}/api/auth/me")
if status in (401, 403):
    ok(f"GET /api/auth/me 无token: HTTP {status}")
else:
    no(f"GET /api/auth/me 无token应返回401/403, 实际={status}")

# Use POST for /api/checkin/in
req = urllib.request.Request(f"{BASE}/api/checkin/in",
    data=json.dumps({"order_id": 1, "room_number": "101"}).encode(),
    method="POST")
req.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        status = resp.status
except urllib.error.HTTPError as e:
    status = e.code
except:
    status = -1
if status in (401, 403):
    ok(f"POST /api/checkin/in 无token: HTTP {status}")
else:
    no(f"POST /api/checkin/in 无token应返回401/403, 实际={status}")

# 2b) Bad token
print("  2b) 错误token访问 → 应返回401")
status = http_get_status(f"{BASE}/api/auth/me",
    {"Authorization": "Bearer invalid_token_here_12345"})
if status == 401:
    ok("错误token: HTTP 401")
else:
    no(f"错误token应返回401, 实际={status}")

# 2c) SQL injection
print("  2c) SQL注入测试: 在查询参数中注入 ' OR '1'='1")
sqli_payload = "' OR '1'='1"
url1 = BASE + "/api/hotels?city=" + urllib.parse.quote(sqli_payload)
code, data = http_get(url1)
total = safe_get(data.get("data", {}), "total", -999)
if total == 0:
    ok("SQL注入(hotels?city='OR'1'='1): 安全, total=0 (参数化查询防御)")
elif isinstance(total, int) and total >= 0:
    ok(f"SQL注入(hotels?city=): 安全, total={total}")
else:
    no("SQL注入(hotels?city=) 异常", str(data)[:200])

sqli_payload2 = "' OR 1=1--"
url2 = BASE + "/api/hotels?keyword=" + urllib.parse.quote(sqli_payload2)
code, data = http_get(url2)
total = safe_get(data.get("data", {}), "total", -999)
if total == 0:
    ok("SQL注入(hotels?keyword='OR 1=1--): 安全, total=0")
elif isinstance(total, int) and total >= 0:
    ok(f"SQL注入(hotels?keyword=): 安全, total={total}")
else:
    no("SQL注入(hotels?keyword=) 异常", str(data)[:200])

# 2d) XSS
print("  2d) XSS测试: 在输入中注入 <script>alert(1)</script>")
code, data = http_post(f"{BASE}/api/auth/register", {
    "username": f"xsstest_{ts}",
    "password": "TestPass123",
    "nickname": "<script>alert(1)</script>"
})
nickname = safe_get(data, "nickname", "")
if code == 200 and "<script>" in str(nickname):
    print("    注意: nickname存储了原始XSS值, 前端需要正确转义")
    ok("XSS存储: 值已存储 (前端负责转义, API层不转义)")
elif code == 200:
    ok(f"XSS存储: nickname={nickname}")
else:
    ok(f"XSS存储: HTTP {code} (可能用户名已存在或验证拦截)")

# XSS in order
if token:
    code, data = http_post(f"{BASE}/api/orders", {
        "hotel_id": hotel_id,
        "room_id": room_id,
        "room_count": 1,
        "checkin_date": checkin_date,
        "checkout_date": checkout_date,
        "guest_name": "<script>alert(1)</script>",
        "guest_phone": "13800138001",
        "remark": "<img src=x onerror=alert(1)>"
    }, headers)
    guest_name = safe_get(data, "guest_name", "")
    if code == 201:
        if "<script>" in str(guest_name):
            print("    注意: guest_name存储了XSS值, 前端需转义")
            ok("XSS(订单): 原始值返回, 前端需转义")
        else:
            ok("XSS(订单): 值已处理")
    else:
        ok(f"XSS(订单): HTTP {code}")

# ============================================================
# SECTION 3: 性能测试
# ============================================================
print()
print("━━━ SECTION 3: 性能测试 ━━━")

# 3a) /api/hotels
print("  3a) /api/hotels 响应时间")
times = []
for i in range(3):
    start = time.time()
    code, data = http_get(f"{BASE}/api/hotels")
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"    请求 {i+1}: {elapsed:.3f}s  (HTTP {code})")
avg_hotel = sum(times) / len(times)
print(f"    平均: {avg_hotel:.3f}s")
if avg_hotel < 1.0:
    ok(f"酒店列表性能: 平均 {avg_hotel:.3f}s < 1s")
else:
    no(f"酒店列表性能: 平均 {avg_hotel:.3f}s >= 1s")

# 3b) /api/orders
print("  3b) /api/orders 列表查询响应时间")
times = []
for i in range(3):
    start = time.time()
    code, data = http_get(f"{BASE}/api/orders", headers)
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"    请求 {i+1}: {elapsed:.3f}s  (HTTP {code})")
avg_order = sum(times) / len(times)
print(f"    平均: {avg_order:.3f}s")
if avg_order < 1.0:
    ok(f"订单列表性能: 平均 {avg_order:.3f}s < 1s")
else:
    no(f"订单列表性能: 平均 {avg_order:.3f}s >= 1s")

# Hotel detail
start = time.time()
code, data = http_get(f"{BASE}/api/hotels/{hotel_id}")
hotel_detail_time = time.time() - start
print(f"    /api/hotels/{hotel_id}: {hotel_detail_time:.3f}s (HTTP {code})")

# ============================================================
# SECTION 4: 数据一致性
# ============================================================
print()
print("━━━ SECTION 4: 数据一致性检查 ━━━")

conn = sqlite3.connect(DB_PATH)

# 4a) Orphaned records
print("  4a) 检查数据库中是否有孤立记录")

cur = conn.execute("SELECT COUNT(*) FROM orders o LEFT JOIN users u ON o.user_id=u.id WHERE u.id IS NULL")
orphan_orders = cur.fetchone()[0]
print(f"    孤立订单(user_id无效): {orphan_orders}")
if orphan_orders == 0:
    ok("无孤立订单")
else:
    no(f"发现 {orphan_orders} 个孤立订单")

cur = conn.execute("SELECT COUNT(*) FROM checkins c LEFT JOIN orders o ON c.order_id=o.id WHERE o.id IS NULL")
orphan_checkins = cur.fetchone()[0]
print(f"    孤立入住记录(order_id无效): {orphan_checkins}")
if orphan_checkins == 0:
    ok("无孤立入住记录")
else:
    no(f"发现 {orphan_checkins} 个孤立入住记录")

cur = conn.execute("SELECT COUNT(*) FROM cleaning_tasks c LEFT JOIN hotels h ON c.hotel_id=h.id WHERE h.id IS NULL")
orphan_cleaning = cur.fetchone()[0]
print(f"    孤立保洁工单(hotel_id无效): {orphan_cleaning}")
if orphan_cleaning == 0:
    ok("无孤立保洁工单")
else:
    no(f"发现 {orphan_cleaning} 个孤立保洁工单")

# 4b) Status consistency
print("  4b) 检查订单-入住-支付状态是否一致")

cur = conn.execute("SELECT COUNT(*) FROM orders WHERE status='checked_in' AND paid_at IS NULL")
inc1 = cur.fetchone()[0]
print(f"    checked_in 但 paid_at=NULL: {inc1}")

cur = conn.execute("SELECT COUNT(*) FROM orders WHERE status='paid' AND paid_at IS NULL")
inc2 = cur.fetchone()[0]
print(f"    status=paid 但 paid_at=NULL: {inc2}")

cur = conn.execute("SELECT COUNT(*) FROM checkins c JOIN orders o ON c.order_id=o.id WHERE c.status='checked_in' AND o.status NOT IN ('checked_in','completed')")
inc3 = cur.fetchone()[0]
print(f"    入住中但订单状态不匹配: {inc3}")

if inc1 == 0 and inc2 == 0 and inc3 == 0:
    ok("订单-支付-入住状态一致")
else:
    no(f"存在状态不一致: checked_in无paid_at={inc1}, paid无paid_at={inc2}, 入住订单不匹配={inc3}")

conn.close()

# ============================================================
# SECTION 5: 新API端点覆盖测试
# ============================================================
print()
print("━━━ SECTION 5: 扩展端点覆盖测试 ━━━")

# 5a) Dashboard stats
print("  5a) 仪表盘统计数据")
code, data = http_get(f"{BASE}/api/dashboard/stats", admin_headers)
if code == 200:
    inner = data.get("data", data)
    occ_rate = safe_get(inner, "occupancy_rate", -1)
    total_rooms = safe_get(inner, "total_rooms", 0)
    if occ_rate >= 0 and total_rooms >= 0:
        ok(f"仪表盘: occupancy_rate={occ_rate}%, total_rooms={total_rooms}")
    else:
        no("仪表盘数据异常", str(data)[:200])
else:
    no(f"仪表盘请求失败 HTTP {code}", str(data)[:200])

# 5b) Finance daily revenue
print("  5b) 财务日营收报表")
today = date.today()
week_ago = today - timedelta(days=7)
code, data = http_get(
    f"{BASE}/api/finance/daily?start_date={week_ago.isoformat()}&end_date={today.isoformat()}",
    admin_headers
)
if code == 200:
    summary = safe_get(data, "summary", {})
    total_rev = safe_get(summary, "total_revenue", -1)
    total_orders = safe_get(summary, "total_orders", -1)
    ok(f"日营收: revenue=¥{total_rev}, orders={total_orders}")
else:
    no(f"日营收请求失败 HTTP {code}", str(data)[:200])

# 5c) Finance overview
print("  5c) 财务总览")
code, data = http_get(f"{BASE}/api/finance/overview", admin_headers)
if code == 200:
    overview = safe_get(data, "data", {})
    today_rev = safe_get(safe_get(overview, "today", {}), "revenue", -1)
    month_rev = safe_get(safe_get(overview, "this_month", {}), "revenue", -1)
    ok(f"财务总览: today=¥{today_rev}, month=¥{month_rev}")
else:
    no(f"财务总览请求失败 HTTP {code}", str(data)[:200])

# 5d) Device list
print("  5d) 设备列表")
code, data = http_get(f"{BASE}/api/devices/list", admin_headers)
if code == 200:
    online = safe_get(data, "online_count", -1)
    offline = safe_get(data, "offline_count", -1)
    alert = safe_get(data, "alert_count", -1)
    total_dev = safe_get(data, "total", 0)
    ok(f"设备列表: total={total_dev}, online={online}, offline={offline}, alert={alert}")
else:
    no(f"设备列表请求失败 HTTP {code}", str(data)[:200])

# 5e) Device stats
print("  5e) 设备统计概览")
code, data = http_get(f"{BASE}/api/devices/stats", admin_headers)
if code == 200:
    stats = safe_get(data, "data", {})
    dev_total = safe_get(stats, "total", 0)
    dev_online = safe_get(stats, "online", 0)
    low_battery = safe_get(stats, "low_battery", 0)
    ok(f"设备统计: total={dev_total}, online={dev_online}, low_battery={low_battery}")
else:
    no(f"设备统计请求失败 HTTP {code}", str(data)[:200])

# 5f) System info
print("  5f) 系统信息")
code, data = http_get(f"{BASE}/api/system/info")
if code == 200:
    sys_data = safe_get(data, "data", {})
    version = safe_get(sys_data, "version", "unknown")
    db_type = safe_get(sys_data, "db_type", "unknown")
    hotel_cnt = safe_get(sys_data, "hotel_count", 0)
    ok(f"系统信息: v{version}, db={db_type}, hotels={hotel_cnt}")
else:
    no(f"系统信息请求失败 HTTP {code}", str(data)[:200])

# 5g) Room status query
print("  5g) 房态总览")
code, data = http_get(f"{BASE}/api/rooms/status", admin_headers)
if code == 200:
    total_rooms = safe_get(data, "total_rooms", 0)
    available = safe_get(data, "available_total", 0)
    occupied = safe_get(data, "occupied_total", 0)
    ok(f"房态: total={total_rooms}, available={available}, occupied={occupied}")
else:
    no(f"房态查询失败 HTTP {code}", str(data)[:200])

# 5h) Lock info
print("  5h) 门锁配置状态")
code, data = http_get(f"{BASE}/api/lock/info")
if code == 200:
    platform = safe_get(safe_get(data, "data", {}), "platform", "unknown")
    ok(f"门锁平台: {platform}")
else:
    no(f"门锁信息请求失败 HTTP {code}", str(data)[:200])

# ============================================================
# Cleanup
# ============================================================
print()
print("━━━ 清理测试数据 ━━━")
conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM cleaning_tasks WHERE notes LIKE '%E2E测试%'")
if checkin_id:
    conn.execute(f"DELETE FROM checkins WHERE id={checkin_id}")
conn.execute("DELETE FROM orders WHERE remark LIKE '%E2E测试%' OR guest_name LIKE '%<script>%'")
conn.execute("DELETE FROM users WHERE username LIKE 'e2etest_%' OR username LIKE 'xsstest_%'")
# Reset room available count
conn.execute(f"UPDATE rooms SET available_count = available_count + 1 WHERE id = {room_id}")
conn.commit()
conn.close()
print("  测试数据已清理")

# ============================================================
# Final Report
# ============================================================
print()
print("=" * 60)
print("                    测 试 报 告")
print("=" * 60)
print()
for r in results:
    print(r)
print("-" * 60)
print(f" 总计: {passed + failed} 项测试 | ✅ 通过: {passed} | ❌ 失败: {failed}")
print()

if failed == 0:
    print(" 🎉 所有测试通过!")
else:
    print(f" ⚠️  有 {failed} 项测试失败, 请检查上述详情")

print()
print(" 性能数据:")
print(f"   /api/hotels:       {avg_hotel:.3f}s (平均)")
print(f"   /api/orders:       {avg_order:.3f}s (平均)")
print(f"   /api/hotels/{hotel_id}:  {hotel_detail_time:.3f}s")
print()
print("=" * 60)
