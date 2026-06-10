"""
伊家人酒店系统 - 门店与房型 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db, Hotel, Room
from app.api.auth import get_current_user, User

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
@router.get("", summary="门店列表")
async def list_hotels(
    city: Optional[str] = Query(None, description="按城市筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词(名称/地址)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Hotel).where(Hotel.is_active == True).options(selectinload(Hotel.rooms))

    if city:
        query = query.where(Hotel.city == city)
    if keyword:
        query = query.where(
            (Hotel.name.contains(keyword)) | (Hotel.address.contains(keyword))
        )

    # 总数
    count_query = select(__import__("sqlalchemy").func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Hotel.rating.desc()).offset(offset).limit(page_size))
    hotels = result.scalars().all()

    # 从预加载的rooms中计算最低价,避免N+1查询
    items = []
    for h in hotels:
        active_rooms = [r for r in h.rooms if r.is_active]
        min_price = min((r.price for r in active_rooms), default=None)
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

    return {"code": 0, "data": {"total": total, "items": items}, "msg": "ok"}


@router.get("/{hotel_id}", response_model=HotelDetail, summary="门店详情")
async def get_hotel_detail(hotel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Hotel).where(Hotel.id == hotel_id, Hotel.is_active == True).options(selectinload(Hotel.rooms))
    )
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="门店不存在")

    active_rooms = [r for r in hotel.rooms if r.is_active]

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
        rooms=[RoomOut.model_validate(r) for r in active_rooms],
    )


@router.get("/{hotel_id}/rooms", response_model=list[RoomOut], summary="门店房型列表")
async def list_rooms(hotel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Room).where(Room.hotel_id == hotel_id, Room.is_active == True)
    )
    rooms = result.scalars().all()
    return [RoomOut.model_validate(r) for r in rooms]


@router.get("/rooms/{room_id}", response_model=RoomOut, summary="房型详情")
async def get_room_detail(room_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Room).where(Room.id == room_id, Room.is_active == True)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房型不存在")
    return RoomOut.model_validate(room)


# ── 门店管理（管理员） ──────────────────────────────

class CreateHotelRequest(BaseModel):
    name: str
    address: str
    city: str
    district: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UpdateHotelRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@router.post("", summary="新增门店（管理员）")
async def create_hotel(
    req: CreateHotelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可新增门店")

    hotel = Hotel(
        name=req.name,
        address=req.address,
        city=req.city,
        district=req.district,
        phone=req.phone,
        description=req.description,
        cover_image=req.cover_image,
        latitude=req.latitude,
        longitude=req.longitude,
        rating=5.0,
    )
    db.add(hotel)
    await db.flush()
    await db.refresh(hotel)
    return {"code": 0, "data": {"id": hotel.id, "name": hotel.name}, "msg": "门店创建成功"}


@router.put("/{hotel_id}", summary="编辑门店（管理员）")
async def update_hotel(
    hotel_id: int,
    req: UpdateHotelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可编辑门店")

    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="门店不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hotel, key, value)

    await db.flush()
    await db.refresh(hotel)
    return {"code": 0, "data": {"id": hotel.id, "name": hotel.name}, "msg": "门店更新成功"}


@router.delete("/{hotel_id}", summary="删除门店（管理员）")
async def delete_hotel(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除门店")

    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="门店不存在")

    # 软删除
    hotel.is_active = False
    await db.flush()
    return {"code": 0, "msg": "门店已删除"}


# ── 房型管理（管理员） ──────────────────────────────

class CreateRoomRequest(BaseModel):
    hotel_id: int
    name: str
    room_type: str
    price: float
    total_count: int = 10
    available_count: int = 10
    area: Optional[float] = None
    bed_type: Optional[str] = None
    max_guests: int = 2
    has_window: bool = True
    has_wifi: bool = True
    has_bathtub: bool = False
    description: Optional[str] = None
    images: Optional[str] = None


class UpdateRoomRequest(BaseModel):
    name: Optional[str] = None
    room_type: Optional[str] = None
    price: Optional[float] = None
    total_count: Optional[int] = None
    available_count: Optional[int] = None
    area: Optional[float] = None
    bed_type: Optional[str] = None
    max_guests: Optional[int] = None
    has_window: Optional[bool] = None
    has_wifi: Optional[bool] = None
    has_bathtub: Optional[bool] = None
    description: Optional[str] = None
    images: Optional[str] = None


@router.post("/{hotel_id}/rooms", summary="新增房型（管理员）")
async def create_room(
    hotel_id: int,
    req: CreateRoomRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可新增房型")

    # 验证门店存在
    hotel_result = await db.execute(select(Hotel).where(Hotel.id == hotel_id, Hotel.is_active == True))
    if not hotel_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="门店不存在")

    room = Room(
        hotel_id=hotel_id,
        name=req.name,
        room_type=req.room_type,
        price=req.price,
        total_count=req.total_count,
        available_count=req.available_count,
        area=req.area,
        bed_type=req.bed_type,
        max_guests=req.max_guests,
        has_window=req.has_window,
        has_wifi=req.has_wifi,
        has_bathtub=req.has_bathtub,
        description=req.description,
        images=req.images,
    )
    db.add(room)
    await db.flush()
    await db.refresh(room)
    return {"code": 0, "data": RoomOut.model_validate(room).model_dump(), "msg": "房型创建成功"}


@router.put("/rooms/{room_id}", summary="编辑房型（管理员）")
async def update_room(
    room_id: int,
    req: UpdateRoomRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可编辑房型")

    result = await db.execute(select(Room).where(Room.id == room_id, Room.is_active == True))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房型不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(room, key, value)

    await db.flush()
    await db.refresh(room)
    return {"code": 0, "data": RoomOut.model_validate(room).model_dump(), "msg": "房型更新成功"}


@router.delete("/rooms/{room_id}", summary="删除房型（管理员）")
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除房型")

    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房型不存在")

    room.is_active = False
    await db.flush()
    return {"code": 0, "msg": "房型已删除"}
