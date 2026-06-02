"""
伊家人酒店系统 - 数据库模型
User / Hotel(门店) / Room(房型/房间) / Order(订单) / Checkin(入住记录)
"""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum as SAEnum, create_engine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings


# ── Base ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Enums ────────────────────────────────────────────
class UserRole:
    ADMIN = "admin"
    GUEST = "guest"
    FRONT_DESK = "front_desk"
    CLEANER = "cleaner"


class OrderStatus:
    PENDING = "pending"        # 待支付
    PAID = "paid"              # 已支付
    CANCELLED = "cancelled"    # 已取消
    CHECKED_IN = "checked_in"  # 已入住
    COMPLETED = "completed"    # 已完成
    REFUNDED = "refunded"      # 已退款


class CheckinStatus:
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"


# ── 用户模型 ─────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.GUEST)
    nickname: Mapped[Optional[str]] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    wx_openid: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True)
    wx_unionid: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    orders: Mapped[List["Order"]] = relationship(back_populates="user")
    checkins: Mapped[List["Checkin"]] = relationship(back_populates="user")


# ── 门店模型 ─────────────────────────────────────────
class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="门店名称")
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(50), index=True)
    district: Mapped[Optional[str]] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    description: Mapped[Optional[str]] = mapped_column(Text, comment="门店简介")
    cover_image: Mapped[Optional[str]] = mapped_column(Text, comment="封面图")
    images: Mapped[Optional[str]] = mapped_column(Text, comment="图片列表 JSON")
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    rooms: Mapped[List["Room"]] = relationship(back_populates="hotel")
    orders: Mapped[List["Order"]] = relationship(back_populates="hotel")
    checkins: Mapped[List["Checkin"]] = relationship(back_populates="hotel")


# ── 房型/房间模型 ─────────────────────────────────────
class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="房型名称")
    room_type: Mapped[str] = mapped_column(String(50), comment="大床房/双床房/套房等")
    price: Mapped[float] = mapped_column(Float, nullable=False, comment="单价(元/晚)")
    total_count: Mapped[int] = mapped_column(Integer, default=10, comment="总房间数")
    available_count: Mapped[int] = mapped_column(Integer, default=10, comment="可用房间数")
    area: Mapped[Optional[float]] = mapped_column(Float, comment="面积(m²)")
    bed_type: Mapped[Optional[str]] = mapped_column(String(50), comment="床型")
    max_guests: Mapped[int] = mapped_column(Integer, default=2, comment="最大入住人数")
    has_window: Mapped[bool] = mapped_column(Boolean, default=True, comment="有无窗户")
    has_wifi: Mapped[bool] = mapped_column(Boolean, default=True)
    has_bathtub: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[Optional[str]] = mapped_column(Text, comment="图片列表 JSON")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    hotel: Mapped["Hotel"] = relationship(back_populates="rooms")
    orders: Mapped[List["Order"]] = relationship(back_populates="room")


# ── 订单模型 ─────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False, comment="订单号")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    room_count: Mapped[int] = mapped_column(Integer, default=1, comment="预订间数")
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False, comment="入住日期")
    checkout_date: Mapped[date] = mapped_column(Date, nullable=False, comment="离店日期")
    nights: Mapped[int] = mapped_column(Integer, nullable=False, comment="入住天数")
    total_price: Mapped[float] = mapped_column(Float, nullable=False, comment="总价")
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING, index=True)
    guest_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="入住人姓名")
    guest_phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="入住人电话")
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(500), comment="取消原因")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user: Mapped["User"] = relationship(back_populates="orders")
    hotel: Mapped["Hotel"] = relationship(back_populates="orders")
    room: Mapped["Room"] = relationship(back_populates="orders")
    checkins: Mapped[List["Checkin"]] = relationship(back_populates="order")


# ── OTA 渠道配置 ─────────────────────────────────────
class OTAChannel(Base):
    __tablename__ = "ota_channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="渠道ID: ctrip/meituan/fliggy")
    name: Mapped[str] = mapped_column(String(50), comment="渠道名称")
    api_key: Mapped[Optional[str]] = mapped_column(String(256), comment="API Key")
    api_secret: Mapped[Optional[str]] = mapped_column(String(256), comment="API Secret")
    hotel_mapping: Mapped[Optional[str]] = mapped_column(Text, comment="酒店ID映射 JSON {local_hotel_id: ota_hotel_id}")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_interval: Mapped[int] = mapped_column(Integer, default=300, comment="同步间隔(秒)")
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OTAOrderMapping(Base):
    __tablename__ = "ota_order_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    local_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    ota_order_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="OTA订单号")
    channel: Mapped[str] = mapped_column(String(20), nullable=False, comment="渠道ID")
    raw_data: Mapped[Optional[str]] = mapped_column(Text, comment="OTA原始订单数据 JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── 入住记录模型 ─────────────────────────────────────
class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), index=True)
    room_number: Mapped[str] = mapped_column(String(20), comment="分配的房间号")
    checkin_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="入住时间")
    checkout_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="退房时间")
    status: Mapped[str] = mapped_column(String(20), default=CheckinStatus.CHECKED_IN)
    door_lock_records: Mapped[Optional[str]] = mapped_column(Text, comment="开锁记录 JSON [{time, action}]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    order: Mapped["Order"] = relationship(back_populates="checkins")
    user: Mapped["User"] = relationship(back_populates="checkins")
    hotel: Mapped["Hotel"] = relationship(back_populates="checkins")


# ── 引擎 & 会话工厂 ──────────────────────────────────
_async_engine = None
_async_session_factory = None


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.db_url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False} if settings.DEV_MODE else {},
        )
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """创建所有表（启动时调用）"""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
