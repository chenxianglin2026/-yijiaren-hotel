"""
伊家人酒店系统 - 门店与房型 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Hotel, Room

router = APIRouter(prefix="/api/hotels", tags=["门店"])


# ── Schemas ──────────────────────────────────────────
class RoomOut(BaseModel):
    id: int
    hotel_id: int
    name: str
    room_type: str
    price: float
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

    model_config = {"from_attributes": True}


class HotelBrief(BaseModel):
    id: int
    name: str
    address: str
    city: str
    district: Optional[str] = None
    cover_image: Optional[str] = None
    rating: float
    min_price: Optional[float] = None  # 最低房型价格，列表查询时填充

    model_config = {"from_attributes": True}


class HotelDetail(BaseModel):
    id: int
    name: str
    address: str
    city: str
    district: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    images: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: float
    rooms: list[RoomOut] = []

    model_config = {"from_attributes": True}


class HotelListResponse(BaseModel):
    total: int
    items: list[HotelBrief]


# ── 路由 ─────────────────────────────────────────────
@router.get("", response_model=HotelListResponse, summary="门店列表")
async def list_hotels(
    city: Optional[str] = Query(None, description="按城市筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词(名称/地址)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Hotel).where(Hotel.is_active == True)

    if city:
        query = query.where(Hotel.city == city)
    if keyword:
        query = query.where(
            (Hotel.name.contains(keyword)) | (Hotel.address.contains(keyword))
        )

    # 总数
    count_query = select(__import__("sqlalchemy").func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)

    # Handle both tuple and scalar return types from SQLAlchemy count
    raw = total_result.one()
    total = raw[0] if isinstance(raw, (tuple, list)) else raw

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Hotel.rating.desc()).offset(offset).limit(page_size))
    hotels = result.scalars().all()

    # 为每个门店查最低价
    items = []
    for h in hotels:
        min_price = None
        price_result = await db.execute(
            select(__import__("sqlalchemy").func.min(Room.price))
            .where(Room.hotel_id == h.id, Room.is_active == True)
        )
        min_price = price_result.scalar()
        items.append(
            HotelBrief(
                id=h.id,
                name=h.name,
                address=h.address,
                city=h.city,
                district=h.district,
                cover_image=h.cover_image,
                rating=h.rating,
                min_price=min_price,
            )
        )

    return HotelListResponse(total=total, items=items)


@router.get("/{hotel_id}", response_model=HotelDetail, summary="门店详情")
async def get_hotel_detail(hotel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id, Hotel.is_active == True))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="门店不存在")

    # 查询房型
    rooms_result = await db.execute(
        select(Room).where(Room.hotel_id == hotel_id, Room.is_active == True)
    )
    rooms = rooms_result.scalars().all()

    return HotelDetail(
        id=hotel.id,
        name=hotel.name,
        address=hotel.address,
        city=hotel.city,
        district=hotel.district,
        phone=hotel.phone,
        description=hotel.description,
        cover_image=hotel.cover_image,
        images=hotel.images,
        latitude=hotel.latitude,
        longitude=hotel.longitude,
        rating=hotel.rating,
        rooms=[RoomOut.model_validate(r) for r in rooms],
    )


@router.get("/{hotel_id}/rooms", response_model=list[RoomOut], summary="门店房型列表")
async def list_rooms(hotel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Room).where(Room.hotel_id == hotel_id, Room.is_active == True)
    )
    rooms = result.scalars().all()
    return [RoomOut.model_validate(r) for r in rooms]
