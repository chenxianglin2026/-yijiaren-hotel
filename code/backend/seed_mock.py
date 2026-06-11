"""
伊家人酒店系统 - 模拟数据播种脚本
插入 3 个门店、每种门店 5 个房型、几条订单
运行: python seed_mock.py           # 仅当数据库为空时播种
      python seed_mock.py --force   # 强制清空并重新播种
      python seed_mock.py --reset   # 仅清空数据（不播种）
"""
import sys
import os
from datetime import date, datetime, timedelta

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, User, Hotel, Room, Order, OrderStatus, Camera, Device, Checkin, OTAChannel, OTAOrderMapping
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_engine():
    return create_engine(
        settings.db_sync_url, echo=False,
        connect_args={"check_same_thread": False} if settings.DEV_MODE else {}
    )


def reset_db():
    """清空所有表数据（保留表结构）"""
    engine = _get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # 按外键依赖顺序删除：checkins -> orders -> devices -> cameras -> rooms -> hotels -> users
        tables = [Checkin, Order, Device, Camera, Room, Hotel, User, OTAChannel, OTAOrderMapping]
        for table in tables:
            count = session.query(table).delete()
            if count > 0:
                print(f"  ── 清空 {table.__tablename__}: {count} 条")
        session.commit()
    print("✅ 数据库已清空")


def seed(force: bool = False):
    engine = _get_engine()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # ── 已有数据则跳过（除非 force=True）──
        if not force and session.query(Hotel).count() > 0:
            print("⚠️  数据库已有数据，跳过播种（使用 --force 强制覆盖）")
            return

        if force and session.query(Hotel).count() > 0:
            print("🔄 强制模式：先清空已有数据...")
            # 不支持嵌套 session，先关闭外层再做 reset
            session.close()
            reset_db()
            # 重新打开 session
            session = Session(engine)
            print("🔄 开始重新播种...")

        import hashlib, os

        def hash_password(pw):
            salt = os.urandom(16)
            return salt.hex() + "$" + hashlib.sha256(salt + pw.encode()).hexdigest()

        # ── 1. 创建测试用户
        admin = User(
            username="admin",
            phone="13800000001",
            hashed_password=hash_password("admin123"),
            role="admin",
            nickname="管理员",
        )
        guest1 = User(
            username="testuser",
            phone="13800000002",
            hashed_password=hash_password("test123"),
            role="guest",
            nickname="测试用户",
        )
        guest2 = User(
            username="zhangsan",
            phone="13912345678",
            hashed_password=hash_password("pass123"),
            role="guest",
            nickname="张三",
        )
        session.add_all([admin, guest1, guest2])
        session.flush()

        # ── 2. 创建 3 个门店 ──
        hotels_data = [
            {
                "name": "伊家人·西湖旗舰店",
                "address": "杭州市西湖区龙井路88号",
                "city": "杭州",
                "district": "西湖区",
                "phone": "0571-88886666",
                "description": "坐落于西湖风景区核心地段，推窗即见西湖美景。提供管家式服务，让您体验江南水乡的温婉与雅致。",
                "cover_image": "https://img.yijiaren.com/hotels/xihu/cover.jpg",
                "latitude": 30.2450,
                "longitude": 120.1420,
                "rating": 4.9,
            },
            {
                "name": "伊家人·三里屯店",
                "address": "北京市朝阳区工体北路甲2号",
                "city": "北京",
                "district": "朝阳区",
                "phone": "010-66668888",
                "description": "位于北京潮流中心三里屯，毗邻使馆区。现代简约设计风格，是商务出行和城市探索的理想之选。",
                "cover_image": "https://img.yijiaren.com/hotels/sanlitun/cover.jpg",
                "latitude": 39.9320,
                "longitude": 116.4550,
                "rating": 4.7,
            },
            {
                "name": "伊家人·珠江新城店",
                "address": "广州市天河区珠江新城华夏路16号",
                "city": "广州",
                "district": "天河区",
                "phone": "020-38889999",
                "description": "地处广州CBD核心区，地铁直达，周边商业配套齐全。岭南风格与现代融合，品味广式生活。",
                "cover_image": "https://img.yijiaren.com/hotels/zhujiang/cover.jpg",
                "latitude": 23.1200,
                "longitude": 113.3250,
                "rating": 4.8,
            },
        ]

        hotels = []
        for hd in hotels_data:
            hotel = Hotel(**hd)
            session.add(hotel)
            session.flush()
            hotels.append(hotel)

        # ── 3. 为每个门店创建 5 个房型（覆盖全部房型属性组合）──
        # 房型矩阵: 大床房/双床房/套房/家庭房/单人间/标准间
        # 属性覆盖: has_window(T/F), has_wifi(T/F), has_bathtub(T/F), max_guests(1-4)
        hotel_room_types = [
            # 西湖旗舰店 — 经典房型
            [
                {"name": "雅致大床房", "room_type": "大床房", "price": 298, "total_count": 15, "area": 25, "bed_type": "1.8m大床", "max_guests": 2, "has_window": True, "has_wifi": True, "has_bathtub": False},
                {"name": "豪华双床房", "room_type": "双床房", "price": 368, "total_count": 12, "area": 32, "bed_type": "1.5m双床", "max_guests": 2, "has_window": True, "has_wifi": True, "has_bathtub": False},
                {"name": "行政套房", "room_type": "套房", "price": 688, "total_count": 5, "area": 55, "bed_type": "1.8m大床", "max_guests": 3, "has_window": True, "has_wifi": True, "has_bathtub": True},
                {"name": "家庭亲子房", "room_type": "家庭房", "price": 528, "total_count": 6, "area": 42, "bed_type": "1.8m+1.2m", "max_guests": 4, "has_window": True, "has_wifi": True, "has_bathtub": True},
                {"name": "舒适单人间", "room_type": "单人间", "price": 198, "total_count": 20, "area": 18, "bed_type": "1.5m大床", "max_guests": 1, "has_window": True, "has_wifi": True, "has_bathtub": False},
            ],
            # 三里屯店 — 覆盖 has_window=False, has_wifi=False
            [
                {"name": "商务大床房", "room_type": "大床房", "price": 358, "total_count": 15, "area": 28, "bed_type": "1.8m大床", "max_guests": 2, "has_window": True, "has_wifi": True, "has_bathtub": False},
                {"name": "经济无窗房", "room_type": "双床房", "price": 248, "total_count": 10, "area": 22, "bed_type": "1.5m双床", "max_guests": 2, "has_window": False, "has_wifi": True, "has_bathtub": False},
                {"name": "豪华套房", "room_type": "套房", "price": 888, "total_count": 4, "area": 60, "bed_type": "1.8m大床", "max_guests": 3, "has_window": True, "has_wifi": True, "has_bathtub": True},
                {"name": "精选大床房", "room_type": "大床房", "price": 458, "total_count": 8, "area": 30, "bed_type": "2.0m特大床", "max_guests": 2, "has_window": True, "has_wifi": False, "has_bathtub": True},
                {"name": "迷你单人间", "room_type": "单人间", "price": 158, "total_count": 12, "area": 15, "bed_type": "1.2m单人床", "max_guests": 1, "has_window": False, "has_wifi": True, "has_bathtub": False},
            ],
            # 珠江新城店 — 覆盖标准间、has_wifi=False
            [
                {"name": "江景大床房", "room_type": "大床房", "price": 498, "total_count": 12, "area": 35, "bed_type": "1.8m大床", "max_guests": 2, "has_window": True, "has_wifi": True, "has_bathtub": False},
                {"name": "标准双床房", "room_type": "双床房", "price": 338, "total_count": 10, "area": 30, "bed_type": "1.5m双床", "max_guests": 2, "has_window": True, "has_wifi": True, "has_bathtub": False},
                {"name": "总统套房", "room_type": "套房", "price": 1288, "total_count": 3, "area": 80, "bed_type": "2.0m特大床", "max_guests": 4, "has_window": True, "has_wifi": True, "has_bathtub": True},
                {"name": "无障碍标准间", "room_type": "标准间", "price": 288, "total_count": 5, "area": 26, "bed_type": "1.5m大床", "max_guests": 2, "has_window": True, "has_wifi": True, "has_bathtub": False},
                {"name": "特惠单人间", "room_type": "单人间", "price": 128, "total_count": 8, "area": 14, "bed_type": "1.2m单人床", "max_guests": 1, "has_window": False, "has_wifi": False, "has_bathtub": False},
            ],
        ]

        all_rooms = []
        for i, hotel in enumerate(hotels):
            for rt in hotel_room_types[i]:
                room = Room(
                    hotel_id=hotel.id,
                    name=rt["name"],
                    room_type=rt["room_type"],
                    price=rt["price"],
                    total_count=rt["total_count"],
                    available_count=rt["total_count"],
                    area=rt["area"],
                    bed_type=rt["bed_type"],
                    max_guests=rt["max_guests"],
                    has_window=rt["has_window"],
                    has_wifi=rt.get("has_wifi", True),
                    has_bathtub=rt["has_bathtub"],
                    description=f"{hotel.name} - {rt['name']}，{rt['area']}m²，{rt['bed_type']}" + ("，无窗" if not rt["has_window"] else "") + ("，无WiFi" if not rt.get("has_wifi", True) else ""),
                    images=f"https://img.yijiaren.com/rooms/{rt['room_type']}/01.jpg",
                )
                session.add(room)
                session.flush()
                all_rooms.append(room)

        # ── 4. 创建几条订单 ──
        today = date.today()

        orders_data = [
            # testuser 在杭州西湖店的订单
            {
                "order_no": datetime.now().strftime("%Y%m%d%H%M") + "A10001",
                "user": guest1,
                "hotel": hotels[0],
                "room": all_rooms[0],  # 雅致大床房
                "checkin_date": today + timedelta(days=3),
                "checkout_date": today + timedelta(days=5),
                "guest_name": "测试用户",
                "guest_phone": "13800000002",
                "status": OrderStatus.PAID,
            },
            # testuser 在北京三里屯店的订单
            {
                "order_no": datetime.now().strftime("%Y%m%d%H%M") + "A10002",
                "user": guest1,
                "hotel": hotels[1],
                "room": all_rooms[5],  # 商务大床房 (三里屯)
                "checkin_date": today + timedelta(days=10),
                "checkout_date": today + timedelta(days=12),
                "guest_name": "测试用户",
                "guest_phone": "13800000002",
                "status": OrderStatus.PENDING,
            },
            # zhangsan 在广州的订单
            {
                "order_no": datetime.now().strftime("%Y%m%d%H%M") + "A10003",
                "user": guest2,
                "hotel": hotels[2],
                "room": all_rooms[10],  # 江景大床房 (珠江新城)
                "checkin_date": today + timedelta(days=1),
                "checkout_date": today + timedelta(days=3),
                "guest_name": "张三",
                "guest_phone": "13912345678",
                "status": OrderStatus.PAID,
            },
            # zhangsan 取消的订单
            {
                "order_no": datetime.now().strftime("%Y%m%d%H%M") + "A10004",
                "user": guest2,
                "hotel": hotels[0],
                "room": all_rooms[3],  # 家庭亲子房
                "checkin_date": today - timedelta(days=5),
                "checkout_date": today - timedelta(days=3),
                "guest_name": "张三",
                "guest_phone": "13912345678",
                "status": OrderStatus.CANCELLED,
                "cancel_reason": "行程变更",
                "cancelled_at": datetime.utcnow() - timedelta(days=7),
            },
        ]

        for od in orders_data:
            nights = (od["checkout_date"] - od["checkin_date"]).days
            order = Order(
                order_no=od["order_no"],
                user_id=od["user"].id,
                hotel_id=od["hotel"].id,
                room_id=od["room"].id,
                room_count=1,
                checkin_date=od["checkin_date"],
                checkout_date=od["checkout_date"],
                nights=nights,
                total_price=od["room"].price * nights,
                status=od["status"],
                guest_name=od["guest_name"],
                guest_phone=od["guest_phone"],
                cancel_reason=od.get("cancel_reason"),
                cancelled_at=od.get("cancelled_at"),
                paid_at=datetime.utcnow() if od["status"] == OrderStatus.PAID else None,
            )
            session.add(order)

            # 扣减已支付订单的可用房间数
            if od["status"] in (OrderStatus.PAID, OrderStatus.CHECKED_IN):
                od["room"].available_count -= 1

        # ── 5. 创建 2 个示例摄像头（离线状态）──
        import base64 as _b64

        _SECRET = b"yjr...y!"
        def _enc_pw(plain):
            key = _SECRET
            data = plain.encode("utf-8")
            enc = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
            return _b64.b64encode(enc).decode()

        cameras_data = [
            {
                "name": "大堂入口摄像头",
                "ip": "192.168.1.64",
                "port": 554,
                "username": "admin",
                "password": _enc_pw("hikvision123"),
                "channel": 1,
                "location": "大堂",
                "status": "offline",
                "rtsp_url": "rtsp://admin:***@192.168.1.64:554/Streaming/Channels/101",
                "hotel_id": hotels[0].id,
            },
            {
                "name": "停车场监控摄像头",
                "ip": "192.168.1.65",
                "port": 554,
                "username": "admin",
                "password": _enc_pw("hikvision456"),
                "channel": 2,
                "location": "停车场",
                "status": "offline",
                "rtsp_url": "rtsp://admin:***@192.168.1.65:554/Streaming/Channels/201",
                "hotel_id": hotels[0].id,
            },
        ]
        for cd in cameras_data:
            session.add(Camera(**cd))

        # ── 9. 插入模拟设备数据 ──
        devices_data = [
            {
                "device_id": "LOCK-001",
                "name": "101房间智能门锁",
                "device_type": "smart_lock",
                "hotel_id": hotels[0].id,
                "room_number": "101",
                "status": "online",
                "battery": 85,
                "firmware_version": "v2.3.1",
                "ip_address": "192.168.1.101",
                "last_online": datetime.utcnow(),
            },
            {
                "device_id": "LOCK-002",
                "name": "102房间智能门锁",
                "device_type": "smart_lock",
                "hotel_id": hotels[0].id,
                "room_number": "102",
                "status": "online",
                "battery": 63,
                "firmware_version": "v2.3.0",
                "ip_address": "192.168.1.102",
                "last_online": datetime.utcnow(),
            },
            {
                "device_id": "LOCK-003",
                "name": "201房间智能门锁",
                "device_type": "smart_lock",
                "hotel_id": hotels[0].id,
                "room_number": "201",
                "status": "offline",
                "battery": 15,
                "firmware_version": "v2.2.0",
                "ip_address": "192.168.1.201",
                "last_online": datetime.utcnow() - timedelta(days=3),
            },
            {
                "device_id": "PANEL-001",
                "name": "大堂客控面板",
                "device_type": "control_panel",
                "hotel_id": hotels[0].id,
                "room_number": None,
                "status": "online",
                "battery": None,
                "firmware_version": "v1.5.0",
                "ip_address": "192.168.1.10",
                "last_online": datetime.utcnow(),
            },
            {
                "device_id": "SENSOR-001",
                "name": "走廊温湿度传感器",
                "device_type": "sensor",
                "hotel_id": hotels[0].id,
                "room_number": None,
                "status": "online",
                "battery": 92,
                "firmware_version": "v1.0.3",
                "ip_address": "192.168.1.50",
                "last_online": datetime.utcnow(),
            },
            {
                "device_id": "CHARGER-001",
                "name": "停车场充电桩A1",
                "device_type": "charger",
                "hotel_id": hotels[1].id,
                "room_number": None,
                "status": "online",
                "battery": None,
                "firmware_version": "v3.1.0",
                "ip_address": "192.168.2.100",
                "last_online": datetime.utcnow(),
            },
            {
                "device_id": "LOCK-101",
                "name": "301房间智能门锁",
                "device_type": "smart_lock",
                "hotel_id": hotels[1].id,
                "room_number": "301",
                "status": "alert",
                "battery": 5,
                "firmware_version": "v2.1.0",
                "ip_address": "192.168.2.201",
                "last_online": datetime.utcnow() - timedelta(hours=1),
            },
            {
                "device_id": "GW-001",
                "name": "主楼网关",
                "device_type": "gateway",
                "hotel_id": hotels[0].id,
                "room_number": None,
                "status": "online",
                "battery": None,
                "firmware_version": "v4.0.2",
                "ip_address": "192.168.1.1",
                "last_online": datetime.utcnow(),
            },
        ]
        for dd in devices_data:
            session.add(Device(**dd))

        session.commit()
        print("✅ 模拟数据播种完成！")
        print(f"   用户: 3 个 (admin/testuser/zhangsan)")
        print(f"   门店: 3 个")
        print(f"   房型: 15 个 (每家 5 种)")
        print(f"   订单: 4 条")
        print(f"   摄像头: 2 个 (示例/offline)")
        print(f"   设备: 8 个 (门锁x4, 面板x1, 传感器x1, 充电桩x1, 网关x1)")
        print(f"\n   测试账号:")
        print(f"   admin / admin123  (管理员)")
        print(f"   testuser / test123  (普通用户)")
        print(f"   zhangsan / pass123  (普通用户)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="伊家人酒店系统 - 数据播种")
    parser.add_argument("--force", action="store_true", help="强制清空并重新播种")
    parser.add_argument("--reset", action="store_true", help="仅清空数据，不播种")
    args = parser.parse_args()

    if args.reset:
        reset_db()
    else:
        seed(force=args.force)
