"""
伊家人酒店系统 - 通行管理 API
电梯/楼层/区域 CRUD + 房卡绑定
"""
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Elevator, Floor, Area, CardBinding, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/access", tags=["通行管理"])


# ── 管理员权限检查 ──────────────────────────────────
def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作通行管理")
    return user


# ── Helper ──────────────────────────────────────────
def _iso(dt):
    return dt.isoformat() if dt else None


# ═══════════════════════════════════════════════════════
# 电梯 CRUD
# ═══════════════════════════════════════════════════════

class ElevatorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    elevator_no: str = Field(..., min_length=1, max_length=50)
    hotel_id: Optional[int] = None
    floors_count: int = Field(0)
    status: str = Field("active")


class ElevatorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    elevator_no: Optional[str] = Field(None, min_length=1, max_length=50)
    hotel_id: Optional[int] = None
    floors_count: Optional[int] = None
    status: Optional[str] = None


@router.get("/elevators", summary="电梯列表")
async def list_elevators(
    hotel_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    query = select(Elevator)
    if hotel_id is not None:
        query = query.where(Elevator.hotel_id == hotel_id)
    query = query.order_by(Elevator.id)
    result = await db.execute(query)
    items = result.scalars().all()
    return {
        "code": 0,
        "data": [{"id": e.id, "name": e.name, "elevator_no": e.elevator_no,
                  "hotel_id": e.hotel_id, "floors_count": e.floors_count,
                  "status": e.status, "created_at": _iso(e.created_at),
                  "updated_at": _iso(e.updated_at)} for e in items],
        "total": len(items),
    }


@router.post("/elevators", summary="添加电梯")
async def create_elevator(
    req: ElevatorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    # check duplicate
    existing = await db.execute(select(Elevator).where(Elevator.elevator_no == req.elevator_no))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"电梯编号 {req.elevator_no} 已存在")

    e = Elevator(**req.model_dump())
    db.add(e)
    await db.flush()
    await db.refresh(e)
    return {"code": 0, "data": {"id": e.id, "name": e.name, "elevator_no": e.elevator_no,
                                 "hotel_id": e.hotel_id, "floors_count": e.floors_count,
                                 "status": e.status, "created_at": _iso(e.created_at),
                                 "updated_at": _iso(e.updated_at)}, "msg": "添加成功"}


@router.put("/elevators/{elevator_id}", summary="编辑电梯")
async def update_elevator(
    elevator_id: int,
    req: ElevatorUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Elevator).where(Elevator.id == elevator_id))
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(404, "电梯不存在")

    updates = req.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(e, k, v)
    e.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(e)
    return {"code": 0, "data": {"id": e.id, "name": e.name, "elevator_no": e.elevator_no,
                                 "hotel_id": e.hotel_id, "floors_count": e.floors_count,
                                 "status": e.status, "created_at": _iso(e.created_at),
                                 "updated_at": _iso(e.updated_at)}, "msg": "更新成功"}


@router.delete("/elevators/{elevator_id}", summary="删除电梯")
async def delete_elevator(
    elevator_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Elevator).where(Elevator.id == elevator_id))
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(404, "电梯不存在")
    await db.delete(e)
    await db.flush()
    return {"code": 0, "msg": f"电梯 {e.name} 已删除"}


# ═══════════════════════════════════════════════════════
# 楼层 CRUD
# ═══════════════════════════════════════════════════════

class FloorCreate(BaseModel):
    elevator_id: int
    floor_number: int
    floor_name: str = Field(..., min_length=1, max_length=50)


class FloorUpdate(BaseModel):
    floor_number: Optional[int] = None
    floor_name: Optional[str] = Field(None, min_length=1, max_length=50)


class BatchFloorCreate(BaseModel):
    elevator_id: int
    floors: List[FloorCreate]


@router.get("/floors", summary="楼层列表")
async def list_floors(
    elevator_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    query = select(Floor)
    if elevator_id is not None:
        query = query.where(Floor.elevator_id == elevator_id)
    query = query.order_by(Floor.elevator_id, Floor.floor_number)
    result = await db.execute(query)
    items = result.scalars().all()
    return {
        "code": 0,
        "data": [{"id": f.id, "elevator_id": f.elevator_id, "floor_number": f.floor_number,
                  "floor_name": f.floor_name, "created_at": _iso(f.created_at)} for f in items],
        "total": len(items),
    }


@router.post("/floors", summary="添加楼层")
async def create_floor(
    req: FloorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    # check elevator exists
    ev = await db.execute(select(Elevator).where(Elevator.id == req.elevator_id))
    if not ev.scalar_one_or_none():
        raise HTTPException(404, "电梯不存在")

    f = Floor(**req.model_dump())
    db.add(f)
    await db.flush()
    await db.refresh(f)
    return {"code": 0, "data": {"id": f.id, "elevator_id": f.elevator_id,
                                 "floor_number": f.floor_number, "floor_name": f.floor_name,
                                 "created_at": _iso(f.created_at)}, "msg": "添加成功"}


@router.post("/floors/batch", summary="批量添加楼层")
async def batch_create_floors(
    req: BatchFloorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    ev = await db.execute(select(Elevator).where(Elevator.id == req.elevator_id))
    if not ev.scalar_one_or_none():
        raise HTTPException(404, "电梯不存在")

    items = []
    for fdata in req.floors:
        f = Floor(elevator_id=req.elevator_id, floor_number=fdata.floor_number, floor_name=fdata.floor_name)
        db.add(f)
        await db.flush()
        await db.refresh(f)
        items.append({"id": f.id, "elevator_id": f.elevator_id, "floor_number": f.floor_number,
                      "floor_name": f.floor_name, "created_at": _iso(f.created_at)})

    # update elevator floors_count
    e2 = ev.scalar_one_or_none()
    if e2:
        count_result = await db.execute(select(Floor).where(Floor.elevator_id == req.elevator_id))
        e2.floors_count = len(count_result.scalars().all())
        await db.flush()

    return {"code": 0, "data": items, "total": len(items), "msg": f"批量添加 {len(items)} 个楼层"}


@router.put("/floors/{floor_id}", summary="编辑楼层")
async def update_floor(
    floor_id: int,
    req: FloorUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Floor).where(Floor.id == floor_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(404, "楼层不存在")

    updates = req.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(f, k, v)
    await db.flush()
    await db.refresh(f)
    return {"code": 0, "data": {"id": f.id, "elevator_id": f.elevator_id,
                                 "floor_number": f.floor_number, "floor_name": f.floor_name,
                                 "created_at": _iso(f.created_at)}, "msg": "更新成功"}


@router.delete("/floors/{floor_id}", summary="删除楼层")
async def delete_floor(
    floor_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Floor).where(Floor.id == floor_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(404, "楼层不存在")

    elevator_id = f.elevator_id
    await db.delete(f)
    await db.flush()

    # update elevator floors_count
    ev = await db.execute(select(Elevator).where(Elevator.id == elevator_id))
    e = ev.scalar_one_or_none()
    if e:
        count_result = await db.execute(select(Floor).where(Floor.elevator_id == elevator_id))
        e.floors_count = len(count_result.scalars().all())
        await db.flush()

    return {"code": 0, "msg": f"楼层 {f.floor_name} 已删除"}


# ═══════════════════════════════════════════════════════
# 区域 CRUD
# ═══════════════════════════════════════════════════════

class AreaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    area_type: str = Field(..., description="区域类型: pool/gym/vip/restaurant")
    hotel_id: Optional[int] = None
    description: Optional[str] = None
    capacity: int = Field(0)
    is_active: bool = True


class AreaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    area_type: Optional[str] = None
    hotel_id: Optional[int] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/areas", summary="区域列表")
async def list_areas(
    hotel_id: Optional[int] = Query(None),
    area_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    query = select(Area)
    if hotel_id is not None:
        query = query.where(Area.hotel_id == hotel_id)
    if area_type:
        query = query.where(Area.area_type == area_type)
    query = query.order_by(Area.id)
    result = await db.execute(query)
    items = result.scalars().all()
    return {
        "code": 0,
        "data": [{"id": a.id, "name": a.name, "area_type": a.area_type,
                  "hotel_id": a.hotel_id, "description": a.description,
                  "capacity": a.capacity, "is_active": a.is_active,
                  "created_at": _iso(a.created_at), "updated_at": _iso(a.updated_at)} for a in items],
        "total": len(items),
    }


@router.post("/areas", summary="添加区域")
async def create_area(
    req: AreaCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    a = Area(**req.model_dump())
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return {"code": 0, "data": {"id": a.id, "name": a.name, "area_type": a.area_type,
                                 "hotel_id": a.hotel_id, "description": a.description,
                                 "capacity": a.capacity, "is_active": a.is_active,
                                 "created_at": _iso(a.created_at), "updated_at": _iso(a.updated_at)}, "msg": "添加成功"}


@router.put("/areas/{area_id}", summary="编辑区域")
async def update_area(
    area_id: int,
    req: AreaUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Area).where(Area.id == area_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "区域不存在")

    updates = req.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(a, k, v)
    a.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(a)
    return {"code": 0, "data": {"id": a.id, "name": a.name, "area_type": a.area_type,
                                 "hotel_id": a.hotel_id, "description": a.description,
                                 "capacity": a.capacity, "is_active": a.is_active,
                                 "created_at": _iso(a.created_at), "updated_at": _iso(a.updated_at)}, "msg": "更新成功"}


@router.delete("/areas/{area_id}", summary="删除区域")
async def delete_area(
    area_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Area).where(Area.id == area_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "区域不存在")
    await db.delete(a)
    await db.flush()
    return {"code": 0, "msg": f"区域 {a.name} 已删除"}


# ═══════════════════════════════════════════════════════
# 房卡绑定 CRUD
# ═══════════════════════════════════════════════════════

class CardCreate(BaseModel):
    card_no: str = Field(..., min_length=1, max_length=50)
    guest_name: str = Field(..., min_length=1, max_length=50)
    user_id: Optional[int] = None
    elevator_id: Optional[int] = None
    floor_ids: Optional[str] = None  # JSON string "[1,2,3]"
    hotel_id: Optional[int] = None
    active_from: Optional[str] = None  # ISO datetime string
    active_until: Optional[str] = None
    is_active: bool = True


class CardUpdate(BaseModel):
    card_no: Optional[str] = Field(None, min_length=1, max_length=50)
    guest_name: Optional[str] = Field(None, min_length=1, max_length=50)
    user_id: Optional[int] = None
    elevator_id: Optional[int] = None
    floor_ids: Optional[str] = None
    hotel_id: Optional[int] = None
    active_from: Optional[str] = None
    active_until: Optional[str] = None
    is_active: Optional[bool] = None


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


@router.get("/cards", summary="房卡绑定列表")
async def list_cards(
    hotel_id: Optional[int] = Query(None),
    elevator_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    query = select(CardBinding)
    if hotel_id is not None:
        query = query.where(CardBinding.hotel_id == hotel_id)
    if elevator_id is not None:
        query = query.where(CardBinding.elevator_id == elevator_id)
    query = query.order_by(CardBinding.id.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    # parse floor_ids JSON
    return {
        "code": 0,
        "data": [{
            "id": c.id, "card_no": c.card_no, "guest_name": c.guest_name,
            "user_id": c.user_id, "elevator_id": c.elevator_id,
            "floor_ids": json.loads(c.floor_ids) if c.floor_ids else [],
            "hotel_id": c.hotel_id,
            "active_from": _iso(c.active_from), "active_until": _iso(c.active_until),
            "is_active": c.is_active,
            "created_at": _iso(c.created_at), "updated_at": _iso(c.updated_at),
        } for c in items],
        "total": len(items),
    }


@router.post("/cards", summary="绑定房卡")
async def create_card(
    req: CardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    existing = await db.execute(select(CardBinding).where(CardBinding.card_no == req.card_no))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"房卡 {req.card_no} 已绑定")

    c = CardBinding(
        card_no=req.card_no,
        guest_name=req.guest_name,
        user_id=req.user_id,
        elevator_id=req.elevator_id,
        floor_ids=req.floor_ids,
        hotel_id=req.hotel_id,
        active_from=_parse_iso(req.active_from),
        active_until=_parse_iso(req.active_until),
        is_active=req.is_active,
    )
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return {"code": 0, "data": {
        "id": c.id, "card_no": c.card_no, "guest_name": c.guest_name,
        "user_id": c.user_id, "elevator_id": c.elevator_id,
        "floor_ids": json.loads(c.floor_ids) if c.floor_ids else [],
        "hotel_id": c.hotel_id,
        "active_from": _iso(c.active_from), "active_until": _iso(c.active_until),
        "is_active": c.is_active,
        "created_at": _iso(c.created_at), "updated_at": _iso(c.updated_at),
    }, "msg": "绑定成功"}


@router.put("/cards/{card_id}", summary="更新房卡绑定")
async def update_card(
    card_id: int,
    req: CardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(CardBinding).where(CardBinding.id == card_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "房卡绑定不存在")

    updates = req.model_dump(exclude_unset=True)
    if "active_from" in updates:
        updates["active_from"] = _parse_iso(updates.pop("active_from"))
    if "active_until" in updates:
        updates["active_until"] = _parse_iso(updates.pop("active_until"))
    for k, v in updates.items():
        setattr(c, k, v)
    c.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(c)
    return {"code": 0, "data": {
        "id": c.id, "card_no": c.card_no, "guest_name": c.guest_name,
        "user_id": c.user_id, "elevator_id": c.elevator_id,
        "floor_ids": json.loads(c.floor_ids) if c.floor_ids else [],
        "hotel_id": c.hotel_id,
        "active_from": _iso(c.active_from), "active_until": _iso(c.active_until),
        "is_active": c.is_active,
        "created_at": _iso(c.created_at), "updated_at": _iso(c.updated_at),
    }, "msg": "更新成功"}


@router.delete("/cards/{card_id}", summary="解绑房卡")
async def delete_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(CardBinding).where(CardBinding.id == card_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "房卡绑定不存在")
    await db.delete(c)
    await db.flush()
    return {"code": 0, "msg": f"房卡 {c.card_no} 已解绑"}
