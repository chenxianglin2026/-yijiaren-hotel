"""
伊家人酒店系统 - 营业报表 API
今日收入 / 入住率 / 房态
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Hotel, Room, Order, Checkin, OrderStatus, CheckinStatus
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["营业报表"])


# ── Schemas ──────────────────────────────────────────

class RoomStatusItem(BaseModel):
    room_id: int
    room_name: str
    room_type: str
    total_count: int
    available_count: int
    occupancy_rate: float


class TodayReport(BaseModel):
    date: str
    today_revenue: float
    today_orders: int
    today_checkins: int
    today_checkouts: int
    occupancy_rate: float
    total_rooms: int
    occupied_rooms: int
    room_status: list[RoomStatusItem]


class ReportResponse(BaseModel):
    code: int = 0
    data: TodayReport
    msg: str = "ok"


# ── 路由 ─────────────────────────────────────────────

@router.get("", response_model=ReportResponse, summary="营业报表")
async def daily_report(
    hotel_id: Optional[int] = Query(None, description="门店ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回今日收入、入住率、房态等综合营业报表。
    """
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = today_start + timedelta(days=1)

    # 门店过滤
    hotel_ids = []
    if hotel_id:
        hotel_result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
        if not hotel_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="门店不存在")
        hotel_ids = [hotel_id]
    else:
        all_hotels = await db.execute(select(Hotel).where(Hotel.is_active == True))
        hotel_ids = [h.id for h in all_hotels.scalars().all()]

    # 今日收入
    revenue_conds = [
        Order.created_at >= today_start,
        Order.created_at < today_end,
        Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
    ]
    if hotel_ids:
        revenue_conds.append(Order.hotel_id.in_(hotel_ids))

    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(*revenue_conds)
    )
    today_revenue = round(float(revenue_result.scalar() or 0), 2)

    # 今日订单数
    order_conds = [
        Order.created_at >= today_start,
        Order.created_at < today_end,
    ]
    if hotel_ids:
        order_conds.append(Order.hotel_id.in_(hotel_ids))
    order_result = await db.execute(select(func.count(Order.id)).where(*order_conds))
    today_orders = order_result.scalar() or 0

    # 今日入住数
    checkin_conds = [
        Checkin.checkin_time >= today_start,
        Checkin.checkin_time < today_end,
    ]
    if hotel_ids:
        checkin_conds.append(Checkin.hotel_id.in_(hotel_ids))
    checkin_result = await db.execute(select(func.count(Checkin.id)).where(*checkin_conds))
    today_checkins = checkin_result.scalar() or 0

    # 今日退房数
    checkout_conds = [
        Checkin.checkout_time >= today_start,
        Checkin.checkout_time < today_end,
    ]
    if hotel_ids:
        checkout_conds.append(Checkin.hotel_id.in_(hotel_ids))
    checkout_result = await db.execute(select(func.count(Checkin.id)).where(*checkout_conds))
    today_checkouts = checkout_result.scalar() or 0

    # 房态统计
    room_q = select(Room).where(Room.is_active == True)
    if hotel_ids:
        room_q = room_q.where(Room.hotel_id.in_(hotel_ids))
    room_result = await db.execute(room_q)
    rooms = room_result.scalars().all()

    total_rooms = sum(r.total_count for r in rooms)
    occupied_rooms = sum(r.total_count - r.available_count for r in rooms)
    occupancy_rate = round(occupied_rooms / total_rooms * 100, 1) if total_rooms > 0 else 0.0

    room_status = []
    for r in rooms:
        occ = r.total_count - r.available_count
        room_status.append(RoomStatusItem(
            room_id=r.id,
            room_name=r.name,
            room_type=r.room_type or "",
            total_count=r.total_count,
            available_count=r.available_count,
            occupancy_rate=round(occ / r.total_count * 100, 1) if r.total_count > 0 else 0.0,
        ))

    return ReportResponse(
        data=TodayReport(
            date=today.isoformat(),
            today_revenue=today_revenue,
            today_orders=today_orders,
            today_checkins=today_checkins,
            today_checkouts=today_checkouts,
            occupancy_rate=occupancy_rate,
            total_rooms=total_rooms,
            occupied_rooms=occupied_rooms,
            room_status=room_status,
        )
    )
