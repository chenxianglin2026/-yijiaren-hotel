"""
伊家人酒店系统 - 模拟数据播种脚本
插入 3 个门店、每种门店 5 个房型、几条订单
运行: python seed_mock.py
"""
import sys
import os
from datetime import date, datetime, timedelta

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, User, Hotel, Room, Order, OrderStatus
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed():
    engine = create_engine(settings.db_sync_url, echo=False, connect_args={"check_same_thread": False} if settings.DEV_MODE else {})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # ── 已有数据则跳过 ──
        if session.query(Hotel).count() > 0:
            print("⚠️  数据库已有数据，跳过播种")
            return

        # ── 1. 创建测试用户 ──
        admin = User(
            username="admin",
            phone="13800000001",
            hashed_password=pwd_context.hash("admin123"),
            role="admin",
            nickname="管理员",
        )
        guest1 = User(
            username="testuser",
            phone="13800000002",
            hashed_password=pwd_context.hash("test123"),
            role="guest",
            nickname="测试用户",
        )
        guest2 = User(
            username="zhangsan",
            phone="13912345678",
            hashed_password=pwd_context.hash("pass123"),
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

        # ── 3. 为每个门店创建 5 个房型 ──
        room_types = [
            {"name": "雅致大床房", "room_type": "大床房", "price": 298, "total_count": 15, "area": 25, "bed_type": "1.8m大床", "max_guests": 2, "has_window": True, "has_bathtub": False},
            {"name": "豪华双床房", "room_type": "双床房", "price": 368, "total_count": 12, "area": 32, "bed_type": "1.5m双床", "max_guests": 2, "has_window": True, "has_bathtub": False},
            {"name": "行政套房", "room_type": "套房", "price": 688, "total_count": 5, "area": 55, "bed_type": "1.8m大床", "max_guests": 3, "has_window": True, "has_bathtub": True},
            {"name": "家庭亲子房", "room_type": "家庭房", "price": 528, "total_count": 6, "area": 42, "bed_type": "1.8m+1.2m", "max_guests": 4, "has_window": True, "has_bathtub": True},
            {"name": "舒适单人间", "room_type": "单人间", "price": 198, "total_count": 20, "area": 18, "bed_type": "1.5m大床", "max_guests": 1, "has_window": True, "has_bathtub": False},
        ]

        all_rooms = []
        for hotel in hotels:
            for rt in room_types:
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
                    has_bathtub=rt["has_bathtub"],
                    description=f"{hotel.name} - {rt['name']}，{rt['area']}m²，{rt['bed_type']}",
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
                "room": all_rooms[7],  # 豪华双床房
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
                "room": all_rooms[12],  # 行政套房
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

        session.commit()
        print("✅ 模拟数据播种完成！")
        print(f"   用户: 3 个 (admin/testuser/zhangsan)")
        print(f"   门店: 3 个")
        print(f"   房型: 15 个 (每家 5 种)")
        print(f"   订单: 4 条")
        print(f"\n   测试账号:")
        print(f"   admin / admin123  (管理员)")
        print(f"   testuser / test123  (普通用户)")
        print(f"   zhangsan / pass123  (普通用户)")


if __name__ == "__main__":
    seed()
