"""
伊家人酒店系统 - 预订 API
/api/bookings GET列表 + POST创建
"""
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db, User, Order, Room, Hotel, OrderStatus
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/bookings", tags=["预订管理"])


# ── Schemas ──────────────────────────────────────────
class BookingCreate(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    room_id: int
    check_in: date
    check_out: date


class BookingOut(BaseModel):
    id: int
    order_no: str
    guest_name: str
    phone: str
    room_id: int
    room_name: Optional[str] = None
    hotel_name: Optional[str] = None
    check_in: date
    check_out: date
    nights: int
    total_price: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    total: int
    items: list[BookingOut]


# ── 路由 ─────────────────────────────────────────────
@router.post("", response_model=BookingOut, status_code=201, summary="创建预订")
async def create_booking(
    req: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.check_in >= req.check_out:
        raise HTTPException(status_code=400, detail="离店日期必须晚于入住日期")
    if req.check_in < date.today():
        raise HTTPException(status_code=400, detail="入住日期不能早于今天")

    room_result = await db.execute(
        select(Room).where(Room.id == req.room_id, Room.is_active == True)
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房型不存在")

    if room.available_count < 1:
        raise HTTPException(status_code=400, detail="该房型暂无空房")

    hotel_result = await db.execute(select(Hotel).where(Hotel.id == room.hotel_id))
    hotel = hotel_result.scalar_one_or_none()

    nights = (req.check_out - req.check_in).days
    total_price = room.price * nights

    order_no = datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()

    order = Order(
        order_no=order_no,
        user_id=current_user.id,
        hotel_id=room.hotel_id,
        room_id=req.room_id,
        room_count=1,
        checkin_date=req.check_in,
        checkout_date=req.check_out,
        nights=nights,
        total_price=total_price,
        status=OrderStatus.PENDING,
        guest_name=req.guest_name,
        guest_phone=req.phone,
    )
    db.add(order)
    room.available_count -= 1

    await db.flush()
    await db.refresh(order)

    return BookingOut(
        id=order.id,
        order_no=order.order_no,
        guest_name=order.guest_name,
        phone=order.guest_phone,
        room_id=order.room_id,
        room_name=room.name,
        hotel_name=hotel.name if hotel else None,
        check_in=order.checkin_date,
        check_out=order.checkout_date,
        nights=order.nights,
        total_price=order.total_price,
        status=order.status,
        created_at=order.created_at,
    )


@router.get("", response_model=BookingListResponse, summary="预订列表")
async def list_bookings(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in ("admin", "front_desk"):
        query = select(Order).options(
            selectinload(Order.room), selectinload(Order.hotel)
        )
        count_q = select(func.count(Order.id))
    else:
        query = select(Order).where(
            Order.user_id == current_user.id
        ).options(selectinload(Order.room), selectinload(Order.hotel))
        count_q = select(func.count(Order.id)).where(
            Order.user_id == current_user.id
        )

    if status:
        query = query.where(Order.status == status)
        count_q = count_q.where(Order.status == status)

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Order.created_at.desc()).offset(offset).limit(page_size)
    )
    orders = result.scalars().all()

    items = []
    for o in orders:
        items.append(
            BookingOut(
                id=o.id,
                order_no=o.order_no,
                guest_name=o.guest_name,
                phone=o.guest_phone,
                room_id=o.room_id,
                room_name=o.room.name if o.room else None,
                hotel_name=o.hotel.name if o.hotel else None,
                check_in=o.checkin_date,
                check_out=o.checkout_date,
                nights=o.nights,
                total_price=o.total_price,
                status=o.status,
                created_at=o.created_at,
            )
        )

    return BookingListResponse(total=total, items=items)
