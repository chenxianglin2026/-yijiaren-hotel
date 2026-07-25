"""
伊家人酒店系统 - 房态查询 API
支持价格策略计算后的实际价格返回
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Room, Hotel
from app.api.pricing import calculate_room_price

router = APIRouter(prefix="/api/rooms", tags=["房态管理"])


class RoomOut(BaseModel):
    id: int
    hotel_id: int
    hotel_name: Optional[str] = None
    name: str
    room_type: str
    price: float
    original_price: Optional[float] = None
    current_price: Optional[float] = None
    has_discount: bool = False
    total_count: int
    available_count: int
    area: Optional[float] = None
    bed_type: Optional[str] = None
    max_guests: int
    has_window: bool
    has_wifi: bool
    has_bathtub: bool
    description: Optional[str] = None
    images: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("", summary="房间列表")
async def list_rooms(
    hotel_id: Optional[int] = Query(None, description="门店ID筛选"),
    date_str: Optional[str] = Query(None, alias="date", description="查询日期 YYYY-MM-DD"),
    nights: int = Query(1, ge=1, le=365, description="入住天数"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Room).where(Room.is_active == True)
    if hotel_id is not None:
        query = query.where(Room.hotel_id == hotel_id)

    result = await db.execute(query.order_by(Room.price.asc()))
    rooms = result.scalars().all()

    # 获取酒店名称映射
    hotel_ids = list({r.hotel_id for r in rooms})
    hotels_map = {}
    if hotel_ids:
        h_result = await db.execute(select(Hotel).where(Hotel.id.in_(hotel_ids)))
        for h in h_result.scalars().all():
            hotels_map[h.id] = h.name

    # 解析查询日期
    query_date = None
    if date_str:
        try:
            query_date = date.fromisoformat(date_str)
        except ValueError:
            pass

    items = []
    for r in rooms:
        item = {
            "id": r.id,
            "hotel_id": r.hotel_id,
            "hotel_name": hotels_map.get(r.hotel_id),
            "name": r.name,
            "room_type": r.room_type,
            "price": r.price,
            "total_count": r.total_count,
            "available_count": r.available_count,
            "area": r.area,
            "bed_type": r.bed_type,
            "max_guests": r.max_guests,
            "has_window": r.has_window,
            "has_wifi": r.has_wifi,
            "has_bathtub": r.has_bathtub,
            "description": r.description,
            "images": r.images,
            "is_active": r.is_active,
            "original_price": r.price,
            "current_price": r.price,
            "has_discount": False,
        }

        # 如果传了日期，计算实际价格
        if query_date is not None:
            try:
                checkout_date = query_date + timedelta(days=nights)
                pricing = await calculate_room_price(
                    db, r.id, query_date, checkout_date
                )
                item["original_price"] = pricing["base_price"]
                item["current_price"] = pricing["final_price"]
                item["has_discount"] = pricing["final_price"] < pricing["base_price"]
            except Exception:
                # 价格计算失败时不阻断列表返回
                pass

        items.append(item)

    return {
        "code": 0,
        "msg": "ok",
        "items": items,
        "total": len(items),
    }


@router.get("/status", summary="房态总览")
async def room_status(
    hotel_id: Optional[int] = Query(None, description="门店ID"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Room).where(Room.is_active == True)
    if hotel_id is not None:
        query = query.where(Room.hotel_id == hotel_id)

    result = await db.execute(query)
    rooms = result.scalars().all()

    hotel_name = None
    if hotel_id is not None:
        h_result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
        hotel = h_result.scalar_one_or_none()
        hotel_name = hotel.name if hotel else None

    total_rooms = sum(r.total_count for r in rooms)
    available_total = sum(r.available_count for r in rooms)
    booked_total = sum((r.total_count - r.available_count) for r in rooms)

    items = []
    for r in rooms:
        occupied = r.total_count - r.available_count
        items.append({
            "id": r.id,
            "name": r.name,
            "price": r.price,
            "total_count": r.total_count,
            "available_count": r.available_count,
            "booked_count": occupied,
            "occupied_count": occupied,
            "cleaning_count": 0,
        })

    return {
        "code": 0,
        "msg": "ok",
        "hotel_id": hotel_id,
        "hotel_name": hotel_name or "伊家酒店",
        "total_rooms": total_rooms,
        "available_total": available_total,
        "booked_total": booked_total,
        "occupied_total": booked_total,
        "cleaning_total": 0,
        "items": items,
    }


@router.put("/{rid}", summary="修改房型信息")
async def update_room(rid: int, req: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == rid))
    room = result.scalar_one_or_none()
    if not room:
        return {"code": 1, "msg": "房型不存在"}

    allowed_fields = [
        "name", "room_type", "price", "total_count", "available_count",
        "area", "bed_type", "max_guests", "has_window", "has_wifi",
        "has_bathtub", "description", "images", "is_active",
    ]
    for key, value in req.items():
        if key in allowed_fields and hasattr(room, key):
            setattr(room, key, value)

    await db.flush()
    await db.refresh(room)
    return {"code": 0, "msg": "修改成功", "data": {
        "id": room.id,
        "name": room.name,
        "price": room.price,
        "available_count": room.available_count,
    }}
