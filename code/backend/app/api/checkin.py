"""
伊家人酒店系统 - 入住管理 API
入住 / 退房 / 入住列表 / 开锁记录
"""
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db, User, Order, Checkin, CheckinStatus, OrderStatus, Hotel
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
    user_id: int
    hotel_id: int
    hotel_name: Optional[str] = None
    room_number: str
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    checkin_date: Optional[str] = None
    checkout_date: Optional[str] = None
    checkin_time: Optional[datetime] = None
    checkout_time: Optional[datetime] = None
    status: str
    door_lock_records: Optional[List[UnlockRecord]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckinListResponse(BaseModel):
    total: int
    items: list[CheckinOut]


# ── 路由 ─────────────────────────────────────────────
@router.post("/in", response_model=CheckinOut, summary="办理入住")
async def do_checkin(
    req: CheckinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 查找订单：admin/front_desk 可办任何订单的入住；普通用户只可办自己的
    if current_user.role in ("admin", "front_desk"):
        order_query = select(Order).where(Order.id == req.order_id)
    else:
        order_query = select(Order).where(Order.id == req.order_id, Order.user_id == current_user.id)

    order_result = await db.execute(
        order_query.options(selectinload(Order.hotel))
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 状态机验证：只有 paid 状态的订单才能办理入住
    if order.status != OrderStatus.PAID:
        raise HTTPException(
            status_code=400,
            detail=f"订单状态为 {order.status}，无法办理入住（仅已支付订单可入住）"
        )

    # 检查是否已有入住记录
    existing = await db.execute(
        select(Checkin).where(Checkin.order_id == req.order_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该订单已办理入住，请勿重复操作")

    # 校验 room_number 非空
    if not req.room_number or not req.room_number.strip():
        raise HTTPException(status_code=400, detail="房间号不能为空")

    checkin = Checkin(
        order_id=req.order_id,
        user_id=current_user.id if current_user.role not in ("admin", "front_desk") else order.user_id,
        hotel_id=order.hotel_id,
        room_number=req.room_number.strip(),
        checkin_time=datetime.utcnow(),
        status=CheckinStatus.CHECKED_IN,
    )
    db.add(checkin)

    # 更新订单状态：paid → checked_in
    order.status = OrderStatus.CHECKED_IN

    await db.flush()
    await db.refresh(checkin)

    # 加载关联数据
    await db.refresh(order)
    return _build_checkin_out(checkin, order)


@router.post("/out/{checkin_id}", response_model=CheckinOut, summary="办理退房")
async def do_checkout(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # admin/front_desk 可退任何入住记录；普通用户只可退自己的
    if current_user.role in ("admin", "front_desk"):
        query = select(Checkin).where(Checkin.id == checkin_id)
    else:
        query = select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == current_user.id)

    result = await db.execute(query)
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="入住记录不存在")

    if checkin.status != CheckinStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail=f"当前状态为 {checkin.status}，无法退房")

    checkin.checkout_time = datetime.utcnow()
    checkin.status = CheckinStatus.CHECKED_OUT

    # 更新订单状态：checked_in → completed
    order_result = await db.execute(
        select(Order).where(Order.id == checkin.order_id).options(selectinload(Order.hotel))
    )
    order = order_result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.COMPLETED

    await db.flush()
    await db.refresh(checkin)

    return _build_checkin_out(checkin, order)


@router.get("", response_model=CheckinListResponse, summary="入住记录列表")
async def list_checkins(
    hotel_id: Optional[int] = Query(None, description="按门店筛选"),
    status: Optional[str] = Query(None, description="按状态筛选: checked_in/checked_out"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # admin/front_desk 可看所有入住记录；普通用户只看自己的
    if current_user.role in ("admin", "front_desk"):
        query = select(Checkin)
        count_q = select(func.count(Checkin.id))
    else:
        query = select(Checkin).where(Checkin.user_id == current_user.id)
        count_q = select(func.count(Checkin.id)).where(Checkin.user_id == current_user.id)

    if hotel_id:
        query = query.where(Checkin.hotel_id == hotel_id)
        count_q = count_q.where(Checkin.hotel_id == hotel_id)

    if status:
        if status not in (CheckinStatus.CHECKED_IN, CheckinStatus.CHECKED_OUT):
            raise HTTPException(status_code=400, detail=f"无效的状态值: {status}，合法值: checked_in, checked_out")
        query = query.where(Checkin.status == status)
        count_q = count_q.where(Checkin.status == status)

    # 总数
    total_result = await db.execute(count_q)
    total = total_result.scalar()

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Checkin.created_at.desc()).offset(offset).limit(page_size)
    )
    checkins = result.scalars().all()

    items = []
    for c in checkins:
        # 加载关联订单和酒店信息
        order_result = await db.execute(
            select(Order).where(Order.id == c.order_id).options(selectinload(Order.hotel))
        )
        order = order_result.scalar_one_or_none()
        items.append(_build_checkin_out(c, order))

    return CheckinListResponse(total=total, items=items)


@router.post("/{checkin_id}/unlock", response_model=CheckinOut, summary="记录开锁")
async def record_unlock(
    checkin_id: int,
    action: str = Body("unlock", embed=True, description="unlock 或 lock"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if action not in ("unlock", "lock"):
        raise HTTPException(status_code=400, detail="action 必须为 unlock 或 lock")

    if current_user.role in ("admin", "front_desk"):
        query = select(Checkin).where(Checkin.id == checkin_id)
    else:
        query = select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == current_user.id)

    result = await db.execute(query)
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="入住记录不存在")

    if checkin.status != CheckinStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail="当前不在入住状态，无法操作门锁")

    # 追加开锁记录
    records = json.loads(checkin.door_lock_records) if checkin.door_lock_records else []
    records.append({
        "time": datetime.utcnow().isoformat(),
        "action": action,
    })
    checkin.door_lock_records = json.dumps(records, ensure_ascii=False)

    await db.flush()
    await db.refresh(checkin)

    # 加载订单信息
    order_result = await db.execute(
        select(Order).where(Order.id == checkin.order_id).options(selectinload(Order.hotel))
    )
    order = order_result.scalar_one_or_none()
    return _build_checkin_out(checkin, order)


@router.get("/{checkin_id}", response_model=CheckinOut, summary="入住详情")
async def get_checkin(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in ("admin", "front_desk"):
        query = select(Checkin).where(Checkin.id == checkin_id)
    else:
        query = select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == current_user.id)

    result = await db.execute(query)
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="入住记录不存在")

    # 加载订单信息
    order_result = await db.execute(
        select(Order).where(Order.id == checkin.order_id).options(selectinload(Order.hotel))
    )
    order = order_result.scalar_one_or_none()

    return _build_checkin_out(checkin, order)


# ── 辅助函数 ─────────────────────────────────────────
def _build_checkin_out(checkin: Checkin, order: Optional[Order] = None) -> CheckinOut:
    records = None
    if checkin.door_lock_records:
        try:
            records = json.loads(checkin.door_lock_records)
        except (json.JSONDecodeError, TypeError):
            records = []

    hotel_name = None
    guest_name = None
    guest_phone = None
    checkin_date = None
    checkout_date = None
    if order:
        if order.hotel:
            hotel_name = order.hotel.name
        guest_name = order.guest_name
        guest_phone = order.guest_phone
        if order.checkin_date:
            checkin_date = order.checkin_date.isoformat()
        if order.checkout_date:
            checkout_date = order.checkout_date.isoformat()

    return CheckinOut(
        id=checkin.id,
        order_id=checkin.order_id,
        user_id=checkin.user_id,
        hotel_id=checkin.hotel_id,
        hotel_name=hotel_name,
        room_number=checkin.room_number,
        guest_name=guest_name,
        guest_phone=guest_phone,
        checkin_date=checkin_date,
        checkout_date=checkout_date,
        checkin_time=checkin.checkin_time,
        checkout_time=checkin.checkout_time,
        status=checkin.status,
        door_lock_records=records,
        created_at=checkin.created_at,
    )
