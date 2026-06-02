"""
伊家人酒店系统 - 仪表盘统计 API v2
- 核心统计
- 近7/30天营收趋势
- 近7天入住率趋势  
- 实时活动流（最近订单/入住）
- 同比对比（vs 昨日）
"""
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Hotel, Room, Order, Checkin, OrderStatus, CheckinStatus
from app.api.auth import get_current_user
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


# ── Schemas ──────────────────────────────────────────

class TrendPoint(BaseModel):
    date: str
    value: float
    label: str = ""

class DashboardStats(BaseModel):
    hotel_id: Optional[int] = None
    hotel_name: Optional[str] = None
    # 今日
    total_rooms: int = 0
    occupied_rooms: int = 0
    occupancy_rate: float = 0.0
    orders_today: int = 0
    revenue_today: float = 0.0
    checked_in_count: int = 0
    pending_cleaning_count: int = 0
    # 同比昨日
    orders_yesterday: int = 0
    revenue_yesterday: float = 0.0
    occupancy_yesterday: float = 0.0
    # 趋势
    revenue_trend: List[TrendPoint] = []
    occupancy_trend: List[TrendPoint] = []

class ActivityItem(BaseModel):
    time: str
    type: str  # order / checkin / checkout / cleaning
    content: str
    hotel_name: str = ""

class DashboardResponse(BaseModel):
    code: int = 0
    data: DashboardStats
    msg: str = "ok"

class TrendResponse(BaseModel):
    code: int = 0
    data: dict
    msg: str = "ok"

class ActivityResponse(BaseModel):
    code: int = 0
    data: List[ActivityItem]
    msg: str = "ok"


# ── 核心统计 ─────────────────────────────────────────

@router.get("/stats", response_model=DashboardResponse, summary="仪表盘完整统计数据")
async def dashboard_stats(
    hotel_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = today_start + timedelta(days=1)
    yesterday = today - timedelta(days=1)
    yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day)
    yesterday_end = today_start

    stats = DashboardStats()
    hotel_ids = []

    if hotel_id:
        result = await db.execute(select(Hotel).where(Hotel.id == hotel_id, Hotel.is_active == True))
        hotel = result.scalar_one_or_none()
        if not hotel:
            from fastapi import HTTPException
            raise HTTPException(404, "门店不存在")
        hotel_ids = [hotel.id]
        stats.hotel_id = hotel_id
        stats.hotel_name = hotel.name
    else:
        result = await db.execute(select(Hotel).where(Hotel.is_active == True))
        hotels = result.scalars().all()
        hotel_ids = [h.id for h in hotels]

    if not hotel_ids:
        return DashboardResponse(data=stats, msg="暂无门店数据")

    # ── 总房间数 ──
    total_rooms_result = await db.execute(
        select(func.sum(Room.total_count)).where(Room.hotel_id.in_(hotel_ids), Room.is_active == True)
    )
    stats.total_rooms = total_rooms_result.scalar() or 0

    # ── 入住中 ──
    occupied_result = await db.execute(
        select(func.count(Checkin.id)).where(
            Checkin.hotel_id.in_(hotel_ids), Checkin.status == CheckinStatus.CHECKED_IN
        )
    )
    stats.occupied_rooms = occupied_result.scalar() or 0
    stats.checked_in_count = stats.occupied_rooms

    if stats.total_rooms > 0:
        stats.occupancy_rate = round(stats.occupied_rooms / stats.total_rooms * 100, 1)

    # ── 今日订单数 ──
    orders_today_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.hotel_id.in_(hotel_ids),
            Order.created_at >= today_start, Order.created_at < today_end,
        )
    )
    stats.orders_today = orders_today_result.scalar() or 0

    # ── 今日营收 ──
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
            Order.hotel_id.in_(hotel_ids),
            Order.created_at >= today_start, Order.created_at < today_end,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
        )
    )
    stats.revenue_today = round(float(revenue_result.scalar() or 0), 2)

    # ── 待清洁 ──
    from app.api.cleaning import CleaningTask
    cleaning_result = await db.execute(
        select(func.count(CleaningTask.id)).where(
            CleaningTask.hotel_id.in_(hotel_ids), CleaningTask.status == "pending"
        )
    )
    stats.pending_cleaning_count = cleaning_result.scalar() or 0

    # ── 昨日同比 ──
    orders_yesterday_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.hotel_id.in_(hotel_ids),
            Order.created_at >= yesterday_start, Order.created_at < yesterday_end,
        )
    )
    stats.orders_yesterday = orders_yesterday_result.scalar() or 0

    revenue_yesterday_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
            Order.hotel_id.in_(hotel_ids),
            Order.created_at >= yesterday_start, Order.created_at < yesterday_end,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
        )
    )
    stats.revenue_yesterday = round(float(revenue_yesterday_result.scalar() or 0), 2)

    # ── 近7天营收趋势 ──
    revenue_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        ds = datetime(d.year, d.month, d.day)
        de = ds + timedelta(days=1)
        r = await db.execute(
            select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
                Order.hotel_id.in_(hotel_ids),
                Order.created_at >= ds, Order.created_at < de,
                Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
            )
        )
        val = round(float(r.scalar() or 0), 2)
        revenue_trend.append(TrendPoint(date=d.isoformat(), value=val, label=f"{d.month}/{d.day}"))

    stats.revenue_trend = revenue_trend

    # ── 近7天入住率趋势 ──
    occupancy_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        end_of_day = datetime(d.year, d.month, d.day, 23, 59, 59)
        r = await db.execute(
            select(func.count(Checkin.id)).where(
                Checkin.hotel_id.in_(hotel_ids),
                Checkin.status == CheckinStatus.CHECKED_IN,
                Checkin.checkin_time <= end_of_day,
            )
        )
        occ = r.scalar() or 0
        rate = round(occ / stats.total_rooms * 100, 1) if stats.total_rooms > 0 else 0
        occupancy_trend.append(TrendPoint(date=d.isoformat(), value=rate, label=f"{d.month}/{d.day}"))

    stats.occupancy_trend = occupancy_trend

    return DashboardResponse(data=stats)


# ── 实时活动流 ─────────────────────────────────────────

@router.get("/activity", response_model=ActivityResponse, summary="最近活动动态")
async def recent_activity(
    limit: int = Query(20, ge=1, le=50),
    hotel_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activities = []

    # 最近订单
    order_q = select(Order).options(
        selectinload(Order.hotel)
    ).order_by(Order.created_at.desc()).limit(limit)
    if hotel_id:
        order_q = order_q.where(Order.hotel_id == hotel_id)

    order_result = await db.execute(order_q)
    for o in order_result.scalars().all():
        activities.append(ActivityItem(
            time=o.created_at.strftime("%H:%M"),
            type="order",
            content=f"新订单 {o.order_no} | {o.guest_name} | {fmtMoney(o.total_price)}",
            hotel_name=o.hotel.name if o.hotel else "",
        ))

    # 最近入住
    checkin_q = select(Checkin).options(
        selectinload(Checkin.hotel)
    ).where(Checkin.checkin_time != None).order_by(Checkin.checkin_time.desc()).limit(limit)
    if hotel_id:
        checkin_q = checkin_q.where(Checkin.hotel_id == hotel_id)

    checkin_result = await db.execute(checkin_q)
    for c in checkin_result.scalars().all():
        activities.append(ActivityItem(
            time=c.checkin_time.strftime("%H:%M") if c.checkin_time else "",
            type="checkin",
            content=f"入住 {c.room_number}号房",
            hotel_name=c.hotel.name if c.hotel else "",
        ))

    # 按时间排序取前 N
    activities.sort(key=lambda x: x.time, reverse=True)
    activities = activities[:limit]

    return ActivityResponse(data=activities)


# ── Helper ───────────────────────────────────────────
def fmtMoney(n):
    return f"¥{n:,.0f}"
