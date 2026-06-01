"""
伊家人酒店系统 - 房态查询 API
空闲 / 已订 / 入住中 / 清洁中
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Room, Hotel, Order, Checkin, OrderStatus, CheckinStatus, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/rooms", tags=["房态管理"])


# ── Schemas ──────────────────────────────────────────
class RoomStatusOut(BaseModel):
    id: int
    hotel_id: int
    name: str
    room_type: str
    price: float
    total_count: int
    available_count: int
    booked_count: int         # 已预订（已支付/待支付）
    occupied_count: int       # 入住中
    cleaning_count: int       # 清洁中（退房后待打扫）
    area: Optional[float] = None
    bed_type: Optional[str] = None
    max_guests: int

    model_config = {"from_attributes": True}


class RoomStatusResponse(BaseModel):
    hotel_id: int
    hotel_name: Optional[str] = None
    total_rooms: int           # 总房间数
    available_total: int       # 总可用间数
    booked_total: int
    occupied_total: int
    cleaning_total: int
    items: list[RoomStatusOut]


# ── 路由 ─────────────────────────────────────────────
@router.get("/status", response_model=RoomStatusResponse, summary="房态总览（按门店）")
async def room_status(
    hotel_id: Optional[int] = Query(None, description="门店ID，不传则返回全部门店"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 查询门店（单个或全部）
    if hotel_id:
        hotel_result = await db.execute(
            select(Hotel).where(Hotel.id == hotel_id, Hotel.is_active == True)
        )
        hotel = hotel_result.scalar_one_or_none()
        if not hotel:
            raise HTTPException(status_code=404, detail="门店不存在")
        hotels = [hotel]
    else:
        result = await db.execute(select(Hotel).where(Hotel.is_active == True))
        hotels = result.scalars().all()

    all_items: list[RoomStatusOut] = []
    total_rooms = 0
    available_total = 0
    booked_total = 0
    occupied_total = 0
    cleaning_total = 0

    today = date.today()

    for hotel in hotels:
        # 查询该门店所有房型
        rooms_result = await db.execute(
            select(Room).where(Room.hotel_id == hotel.id, Room.is_active == True)
        )
        rooms = rooms_result.scalars().all()

        for room in rooms:
            # 入住中的数量：通过订单关联该房型的入住记录
            occupied_result = await db.execute(
                select(func.count(Checkin.id)).join(
                    Order, Checkin.order_id == Order.id
                ).where(
                    Order.hotel_id == hotel.id,
                    Order.room_id == room.id,
                    Checkin.status == CheckinStatus.CHECKED_IN,
                )
            )
            occupied_count = occupied_result.scalar() or 0

            # 已预订的数量：该房型相关订单中 PAID/PENDING 且未取消未入住
            booked_result = await db.execute(
                select(func.count(Order.id)).where(
                    Order.hotel_id == hotel.id,
                    Order.room_id == room.id,
                    Order.status.in_([OrderStatus.PAID, OrderStatus.PENDING]),
                    Order.checkin_date >= today,
                )
            )
            booked_count = booked_result.scalar() or 0

            # 清洁中：退房后需要打扫的房间
            # 简单估算：total - available - booked - occupied
            used = room.total_count - room.available_count
            cleaning_count = max(0, used - occupied_count - booked_count)

            total_rooms += room.total_count
            available_total += room.available_count
            booked_total += booked_count
            occupied_total += occupied_count
            cleaning_total += cleaning_count

            all_items.append(
                RoomStatusOut(
                    id=room.id,
                    hotel_id=room.hotel_id,
                    name=room.name,
                    room_type=room.room_type,
                    price=room.price,
                    total_count=room.total_count,
                    available_count=room.available_count,
                    booked_count=booked_count,
                    occupied_count=occupied_count,
                    cleaning_count=cleaning_count,
                    area=room.area,
                    bed_type=room.bed_type,
                    max_guests=room.max_guests,
                )
            )

    return RoomStatusResponse(
        hotel_id=hotel_id or 0,
        hotel_name=hotels[0].name if hotel_id else None,
        total_rooms=total_rooms,
        available_total=available_total,
        booked_total=booked_total,
        occupied_total=occupied_total,
        cleaning_total=cleaning_total,
        items=all_items,
    )
