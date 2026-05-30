"""
伊家人酒店系统 - 仪表盘统计 API
今日订单数 / 入住率 / 今日营收 / 入住中 / 待清洁
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Hotel, Room, Order, Checkin, OrderStatus, CheckinStatus
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


# ── Schemas ──────────────────────────────────────────
class DashboardStats(BaseModel):
    hotel_id: Optional[int] = None
    hotel_name: Optional[str] = None
    # 今日统计
    total_rooms: int = 0
    occupied_rooms: int = 0
    occupancy_rate: float = 0.0  # 入住率百分比
    orders_today: int = 0  # 今日新订单数
    revenue_today: float = 0.0  # 今日营收（已支付+已入住+已完成订单的总价）
    checked_in_count: int = 0  # 当前入住中
    pending_cleaning_count: int = 0  # 待清洁（pending状态的保洁工单）


class DashboardResponse(BaseModel):
    code: int = 0
    data: DashboardStats
    msg: str = "ok"


# ── 路由 ─────────────────────────────────────────────
@router.get("/stats", response_model=DashboardResponse, summary="仪表盘统计数据")
async def dashboard_stats(
    hotel_id: Optional[int] = Query(None, description="门店ID，不传则返回全局汇总"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取仪表盘核心统计数据：今日订单/入住率/营收/入住中/待清洁"""
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = today_start + timedelta(days=1)

    stats = DashboardStats()

    # ── 确定查询范围（单门店或全部门店） ──
    hotel_ids = []
    hotel_name = None

    if hotel_id:
        result = await db.execute(
            select(Hotel).where(Hotel.id == hotel_id, Hotel.is_active == True)
        )
        hotel = result.scalar_one_or_none()
        if not hotel:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="门店不存在")
        hotel_ids = [hotel.id]
        hotel_name = hotel.name
        stats.hotel_id = hotel_id
        stats.hotel_name = hotel_name
    else:
        result = await db.execute(select(Hotel).where(Hotel.is_active == True))
        hotels = result.scalars().all()
        hotel_ids = [h.id for h in hotels]

    if not hotel_ids:
        return DashboardResponse(data=stats, msg="暂无门店数据")

    # ── 总房间数 & 入住中 ──
    total_rooms_result = await db.execute(
        select(func.sum(Room.total_count)).where(
            Room.hotel_id.in_(hotel_ids),
            Room.is_active == True,
        )
    )
    stats.total_rooms = total_rooms_result.scalar() or 0

    # 入住中：checkins 中 status=checked_in 的记录
    occupied_result = await db.execute(
        select(func.count(Checkin.id)).where(
            Checkin.hotel_id.in_(hotel_ids),
            Checkin.status == CheckinStatus.CHECKED_IN,
        )
    )
    stats.occupied_rooms = occupied_result.scalar() or 0
    stats.checked_in_count = stats.occupied_rooms

    # 入住率
    if stats.total_rooms > 0:
        stats.occupancy_rate = round(stats.occupied_rooms / stats.total_rooms * 100, 1)

    # ── 今日新订单数 ──
    orders_today_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.hotel_id.in_(hotel_ids),
            Order.created_at >= today_start,
            Order.created_at < today_end,
        )
    )
    stats.orders_today = orders_today_result.scalar() or 0

    # ── 今日营收：今天创建的已支付/已入住/已完成订单的总价之和 ──
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
            Order.hotel_id.in_(hotel_ids),
            Order.created_at >= today_start,
            Order.created_at < today_end,
            Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
        )
    )
    stats.revenue_today = round(float(revenue_result.scalar() or 0), 2)

    # ── 待清洁：cleaning_tasks 中 status=pending 的数量 ──
    from app.api.cleaning import CleaningTask
    pending_cleaning_result = await db.execute(
        select(func.count(CleaningTask.id)).where(
            CleaningTask.hotel_id.in_(hotel_ids),
            CleaningTask.status == "pending",
        )
    )
    stats.pending_cleaning_count = pending_cleaning_result.scalar() or 0

    return DashboardResponse(data=stats, msg="ok")
