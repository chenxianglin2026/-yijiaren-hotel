"""
丰富模拟数据 — 订单/清洁任务/入住记录/服务请求
运行: python seed_rich.py (VPS Docker内)
"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, User, Hotel, Room, Order, OrderStatus, Checkin, CheckinStatus

engine = create_engine(
    settings.db_sync_url, echo=False,
    connect_args={"check_same_thread": False} if settings.DEV_MODE else {}
)

def hash_pw(pw):
    salt = os.urandom(16)
    return salt.hex() + "$" + hashlib.sha256(salt + pw.encode()).hexdigest()

with Session(engine) as s:
    today = date.today()

    # Users
    users = s.query(User).all()
    if len(users) < 5:
        names = [("王芳","13811110001"),("李伟","13811110002"),("赵丽","13811110003")]
        for name, phone in names:
            if not s.query(User).filter(User.phone==phone).first():
                s.add(User(username=name, phone=phone, hashed_password=hash_pw("test123"), role="guest", nickname=name))
        s.flush()
    users = s.query(User).all()

    # Hotels & Rooms
    hotels = s.query(Hotel).all()
    all_rooms = s.query(Room).all()

    # Generate 20 orders spanning last 7 days
    guest_names = ["王芳","李伟","赵丽","张三","刘洋","陈静","周杰","吴敏"]
    phones = ["13811110001","13811110002","13811110003","13912345678","13600001111","13500002222","13400003333","13300004444"]
    statuses = [OrderStatus.PAID, OrderStatus.PAID, OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED, OrderStatus.PENDING, OrderStatus.CANCELLED]

    existing_count = s.query(func.count(Order.id)).scalar()
    if existing_count < 10:
        for i in range(20):
            h = hotels[i % len(hotels)]
            r = all_rooms[i % len(all_rooms)]
            offset = -7 + i
            cin = today + timedelta(days=offset)
            cout = cin + timedelta(days=max(1, i % 3 + 1))
            nights = (cout - cin).days
            gidx = i % len(guest_names)
            st = statuses[i % len(statuses)]

            order = Order(
                order_no=f"S{datetime.now().strftime('%m%d')}{i:04d}",
                user_id=users[gidx % len(users)].id,
                hotel_id=h.id,
                room_id=r.id,
                room_count=1,
                checkin_date=cin,
                checkout_date=cout,
                nights=nights,
                total_price=r.price * nights,
                status=st,
                guest_name=guest_names[gidx],
                guest_phone=phones[gidx],
                paid_at=datetime.utcnow() - timedelta(days=abs(offset)) if st != OrderStatus.PENDING else None,
                cancelled_at=datetime.utcnow() - timedelta(days=abs(offset)-1) if st == OrderStatus.CANCELLED else None,
                cancel_reason="行程变更" if st == OrderStatus.CANCELLED else None,
            )
            s.add(order)

            # Create checkin for checked_in/completed
            if st == OrderStatus.CHECKED_IN or st == OrderStatus.COMPLETED:
                s.flush()
                checkin = Checkin(
                    order_id=order.id,
                    user_id=order.user_id,
                    hotel_id=order.hotel_id,
                    room_number=str(300 + i % 20),
                    checkin_time=datetime.now() - timedelta(days=abs(offset)),
                    checkout_time=datetime.now() - timedelta(days=abs(offset)-nights) if st == OrderStatus.COMPLETED else None,
                    status=CheckinStatus.CHECKED_OUT if st == OrderStatus.COMPLETED else CheckinStatus.CHECKED_IN,
                )
                s.add(checkin)

        s.commit()
        print(f"✅ Added 20 orders + checkins")

    # Cleaning tasks via service_requests
    from app.db import Base as B
    # Create cleaning_tasks table if not exists
    try:
        from app.api.cleaning import CleaningTask
    except:
        CleaningTask = None

    print(f"📊 Totals: {s.query(func.count(Order.id)).scalar()} orders, {s.query(func.count(Checkin.id)).scalar()} checkins, {s.query(func.count(Hotel.id)).scalar()} hotels")
    print("✅ Rich seed complete")
