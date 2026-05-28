"""
伊家人酒店系统 - 入住管理 API
入住 / 退房 / 开锁记录
"""
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Order, Checkin, CheckinStatus, OrderStatus
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/checkin", tags=["入住管理"])


# ── Schemas ──────────────────────────────────────────
class CheckinRequest(BaseModel):
    order_id: int
    room_number: str


class UnlockRecord(BaseModel):
    time: str
    action: str  # "unlock" / "lock"


class CheckinOut(BaseModel):
    id: int
    order_id: int
    hotel_id: int
    room_number: str
    checkin_time: Optional[datetime] = None
    checkout_time: Optional[datetime] = None
    status: str
    door_lock_records: Optional[List[UnlockRecord]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 路由 ─────────────────────────────────────────────
@router.post("/in", response_model=CheckinOut, summary="办理入住")
async def do_checkin(
    req: CheckinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 查找订单
    order_result = await db.execute(
        select(Order).where(Order.id == req.order_id, Order.user_id == current_user.id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status != OrderStatus.PAID:
        raise HTTPException(status_code=400, detail="订单未支付，无法办理入住")

    # 检查是否已有入住记录
    existing = await db.execute(
        select(Checkin).where(Checkin.order_id == req.order_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该订单已办理入住")

    checkin = Checkin(
        order_id=req.order_id,
        user_id=current_user.id,
        hotel_id=order.hotel_id,
        room_number=req.room_number,
        checkin_time=datetime.utcnow(),
        status=CheckinStatus.CHECKED_IN,
    )
    db.add(checkin)

    # 更新订单状态
    order.status = OrderStatus.CHECKED_IN

    await db.flush()
    await db.refresh(checkin)

    return _build_checkin_out(checkin)


@router.post("/out/{checkin_id}", response_model=CheckinOut, summary="办理退房")
async def do_checkout(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == current_user.id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="入住记录不存在")

    if checkin.status != CheckinStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail="当前状态无法退房")

    checkin.checkout_time = datetime.utcnow()
    checkin.status = CheckinStatus.CHECKED_OUT

    # 更新订单状态
    order_result = await db.execute(select(Order).where(Order.id == checkin.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.COMPLETED

    await db.flush()
    await db.refresh(checkin)

    return _build_checkin_out(checkin)


@router.post("/{checkin_id}/unlock", response_model=CheckinOut, summary="记录开锁")
async def record_unlock(
    checkin_id: int,
    action: str = Body("unlock", embed=True, description="unlock 或 lock"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == current_user.id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="入住记录不存在")

    if checkin.status != CheckinStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail="当前不在入住状态")

    # 追加开锁记录
    records = json.loads(checkin.door_lock_records) if checkin.door_lock_records else []
    records.append({
        "time": datetime.utcnow().isoformat(),
        "action": action,
    })
    checkin.door_lock_records = json.dumps(records, ensure_ascii=False)

    await db.flush()
    await db.refresh(checkin)

    return _build_checkin_out(checkin)


@router.get("/{checkin_id}", response_model=CheckinOut, summary="入住详情")
async def get_checkin(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == current_user.id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="入住记录不存在")

    return _build_checkin_out(checkin)


# ── 辅助函数 ─────────────────────────────────────────
def _build_checkin_out(checkin: Checkin) -> CheckinOut:
    records = None
    if checkin.door_lock_records:
        try:
            records = json.loads(checkin.door_lock_records)
        except (json.JSONDecodeError, TypeError):
            records = []

    return CheckinOut(
        id=checkin.id,
        order_id=checkin.order_id,
        hotel_id=checkin.hotel_id,
        room_number=checkin.room_number,
        checkin_time=checkin.checkin_time,
        checkout_time=checkin.checkout_time,
        status=checkin.status,
        door_lock_records=records,
        created_at=checkin.created_at,
    )
