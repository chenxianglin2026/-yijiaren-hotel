""""
伊家人酒店系统 - 订单 API
创建订单 / 查询订单 / 取消订单 / 状态流转
状态机：pending → paid → checked_in → completed
          ↓         ↓         ↓
       cancelled  refunded  (不可取消/退款)
"""
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db, User, Order, Room, Hotel, OrderStatus
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/orders", tags=["订单"])

# 合法的订单状态值列表
VALID_ORDER_STATUSES = {
    OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.CHECKED_IN,
    OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REFUNDED,
}

# 合法的状态转换规则
VALID_TRANSITIONS = {
    OrderStatus.PENDING:   {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID:      {OrderStatus.CHECKED_IN, OrderStatus.CANCELLED, OrderStatus.REFUNDED},
    OrderStatus.CHECKED_IN:{OrderStatus.COMPLETED, OrderStatus.REFUNDED},
    OrderStatus.COMPLETED: set(),       # 终态
    OrderStatus.CANCELLED: set(),       # 终态
    OrderStatus.REFUNDED:  set(),       # 终态
}


# ── Schemas ──────────────────────────────────────────
class CreateOrderRequest(BaseModel):
    hotel_id: int
    room_id: int
    room_count: int = Field(1, ge=1, le=10)
    checkin_date: date
    checkout_date: date
    guest_name: str = Field(..., min_length=1, max_length=50)
    guest_phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    remark: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    order_no: str
    hotel_id: int
    hotel_name: Optional[str] = None
    room_id: int
    room_name: Optional[str] = None
    room_type: Optional[str] = None
    room_count: int
    checkin_date: date
    checkout_date: date
    nights: int
    total_price: float
    status: str
    guest_name: str
    guest_phone: str
    remark: Optional[str] = None
    cancel_reason: Optional[str] = None
    paid_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    total: int
    items: list[OrderOut]


# ── 路由 ─────────────────────────────────────────────
@router.post("", response_model=OrderOut, status_code=201, summary="创建订单")
async def create_order(
    req: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 校验入住日期
    if req.checkin_date >= req.checkout_date:
        raise HTTPException(status_code=400, detail="离店日期必须晚于入住日期")

    # 校验日期不能是过去
    if req.checkin_date < date.today():
        raise HTTPException(status_code=400, detail="入住日期不能早于今天")

    # 查询房型
    room_result = await db.execute(
        select(Room).where(Room.id == req.room_id, Room.is_active == True)
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房型不存在")

    # 校验可用房间数
    if room.available_count < req.room_count:
        raise HTTPException(status_code=400, detail=f"该房型仅剩 {room.available_count} 间可订")

    # 查询门店
    hotel_result = await db.execute(select(Hotel).where(Hotel.id == req.hotel_id))
    hotel = hotel_result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="门店不存在")

    # 计算天数和总价
    nights = (req.checkout_date - req.checkin_date).days
    total_price = room.price * req.room_count * nights

    # 生成订单号
    order_no = datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()

    order = Order(
        order_no=order_no,
        user_id=current_user.id,
        hotel_id=req.hotel_id,
        room_id=req.room_id,
        room_count=req.room_count,
        checkin_date=req.checkin_date,
        checkout_date=req.checkout_date,
        nights=nights,
        total_price=total_price,
        status=OrderStatus.PENDING,
        guest_name=req.guest_name,
        guest_phone=req.guest_phone,
        remark=req.remark,
    )
    db.add(order)

    # 扣减可用房间数
    room.available_count -= req.room_count

    await db.flush()
    await db.refresh(order)

    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        hotel_id=order.hotel_id,
        hotel_name=hotel.name,
        room_id=order.room_id,
        room_name=room.name,
        room_count=order.room_count,
        checkin_date=order.checkin_date,
        checkout_date=order.checkout_date,
        nights=order.nights,
        total_price=order.total_price,
        status=order.status,
        guest_name=order.guest_name,
        guest_phone=order.guest_phone,
        remark=order.remark,
        created_at=order.created_at,
    )


@router.get("", response_model=OrderListResponse, summary="查询订单列表")
async def list_orders(
    keyword: Optional[str] = Query(None, description="搜索订单号/客人姓名"),
    status: Optional[str] = Query(None, description="订单状态筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin/front_desk can see all orders; normal users see only their own
    if current_user.role in ("admin", "front_desk"):
        query = select(Order).options(
            selectinload(Order.hotel), selectinload(Order.room)
        )
        count_q = select(func.count(Order.id))
    else:
        query = select(Order).where(Order.user_id == current_user.id).options(
            selectinload(Order.hotel), selectinload(Order.room)
        )
        count_q = select(func.count(Order.id)).where(Order.user_id == current_user.id)

    if status:
        if status not in VALID_ORDER_STATUSES:
            raise HTTPException(status_code=400, detail=f"无效的订单状态: {status}，合法值: {', '.join(sorted(VALID_ORDER_STATUSES))}")
        query = query.where(Order.status == status)
        count_q = count_q.where(Order.status == status)

    if keyword:
        query = query.where(
            (Order.order_no.contains(keyword)) | (Order.guest_name.contains(keyword))
        )
        count_q = count_q.where(
            (Order.order_no.contains(keyword)) | (Order.guest_name.contains(keyword))
        )

    # Date range filter
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(Order.created_at >= sd)
            count_q = count_q.where(Order.created_at >= sd)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(Order.created_at < ed)
            count_q = count_q.where(Order.created_at < ed)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    # 总数
    total_result = await db.execute(count_q)
    total = total_result.scalar()

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Order.created_at.desc()).offset(offset).limit(page_size))
    orders = result.scalars().all()

    items = []
    for o in orders:
        hotel_name = None
        room_name = None
        room_type = None
        if o.hotel:
            hotel_name = o.hotel.name
        if o.room:
            room_name = o.room.name
            room_type = o.room.room_type

        items.append(
            OrderOut(
                id=o.id,
                order_no=o.order_no,
                hotel_id=o.hotel_id,
                hotel_name=hotel_name,
                room_id=o.room_id,
                room_name=room_name,
                room_type=room_type,
                room_count=o.room_count,
                checkin_date=o.checkin_date,
                checkout_date=o.checkout_date,
                nights=o.nights,
                total_price=o.total_price,
                status=o.status,
                guest_name=o.guest_name,
                guest_phone=o.guest_phone,
                remark=o.remark,
                cancel_reason=o.cancel_reason,
                paid_at=o.paid_at,
                cancelled_at=o.cancelled_at,
                created_at=o.created_at,
            )
        )

    return OrderListResponse(total=total, items=items)


@router.get("/{order_id}", response_model=OrderOut, summary="订单详情")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin/front_desk can view any order; normal users see only their own
    if current_user.role in ("admin", "front_desk"):
        query = select(Order).where(Order.id == order_id)
    else:
        query = select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    
    result = await db.execute(
        query.options(selectinload(Order.hotel), selectinload(Order.room))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        hotel_id=order.hotel_id,
        hotel_name=order.hotel.name if order.hotel else None,
        room_id=order.room_id,
        room_name=order.room.name if order.room else None,
        room_type=order.room.room_type if order.room else None,
        room_count=order.room_count,
        checkin_date=order.checkin_date,
        checkout_date=order.checkout_date,
        nights=order.nights,
        total_price=order.total_price,
        status=order.status,
        guest_name=order.guest_name,
        guest_phone=order.guest_phone,
        remark=order.remark,
        cancel_reason=order.cancel_reason,
        paid_at=order.paid_at,
        cancelled_at=order.cancelled_at,
        created_at=order.created_at,
    )


@router.post("/{order_id}/cancel", response_model=OrderOut, summary="取消订单")
async def cancel_order(
    order_id: int,
    reason: Optional[str] = Query(None, description="取消原因"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin/front_desk can cancel any order; normal users only their own
    if current_user.role in ("admin", "front_desk"):
        query = select(Order).where(Order.id == order_id)
    else:
        query = select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    
    result = await db.execute(
        query.options(selectinload(Order.hotel), selectinload(Order.room))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 状态机验证：只能取消待支付和已支付的订单
    if OrderStatus.CANCELLED not in VALID_TRANSITIONS.get(order.status, set()):
        raise HTTPException(status_code=400, detail=f"当前订单状态为 {order.status}，无法取消（仅 pending/paid 可取消）")

    order.status = OrderStatus.CANCELLED
    order.cancel_reason = reason
    order.cancelled_at = datetime.utcnow()

    # 恢复可用房间数
    room_result = await db.execute(select(Room).where(Room.id == order.room_id))
    room = room_result.scalar_one_or_none()
    if room:
        room.available_count += order.room_count

    await db.flush()
    await db.refresh(order)

    return _build_order_out(order)


@router.post("/{order_id}/status", response_model=OrderOut, summary="管理员更新订单状态")
async def update_order_status(
    order_id: int,
    new_status: str = Query(..., description="新状态: paid/checked_in/completed/cancelled/refunded"),
    reason: Optional[str] = Query(None, description="状态变更原因"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员手动更新订单状态，走状态机校验"""
    if current_user.role not in ("admin", "front_desk"):
        raise HTTPException(status_code=403, detail="仅管理员或前台可更新订单状态")

    if new_status not in VALID_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"无效的状态值: {new_status}，合法值: {', '.join(sorted(VALID_ORDER_STATUSES))}")

    result = await db.execute(
        select(Order).where(Order.id == order_id).options(
            selectinload(Order.hotel), selectinload(Order.room)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    old_status = order.status
    allowed = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不允许从 {old_status} 转换到 {new_status}。当前状态允许的转换: {', '.join(sorted(allowed)) if allowed else '无（终态）'}"
        )

    # 执行状态转换
    order.status = new_status
    if new_status == OrderStatus.PAID and not order.paid_at:
        order.paid_at = datetime.utcnow()
    if new_status == OrderStatus.CANCELLED:
        order.cancel_reason = reason or "管理员取消"
        order.cancelled_at = datetime.utcnow()
    if new_status == OrderStatus.REFUNDED and not order.cancelled_at:
        order.cancelled_at = datetime.utcnow()

    # 取消/退款时恢复可用房间数
    if new_status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        room_result = await db.execute(select(Room).where(Room.id == order.room_id))
        room = room_result.scalar_one_or_none()
        if room:
            room.available_count += order.room_count

    await db.flush()
    await db.refresh(order)
    return _build_order_out(order)


# ── 辅助函数 ─────────────────────────────────────────
def _build_order_out(order: Order) -> OrderOut:
    """构建 OrderOut 响应对象"""
    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        hotel_id=order.hotel_id,
        hotel_name=order.hotel.name if order.hotel else None,
        room_id=order.room_id,
        room_name=order.room.name if order.room else None,
        room_type=order.room.room_type if order.room else None,
        room_count=order.room_count,
        checkin_date=order.checkin_date,
        checkout_date=order.checkout_date,
        nights=order.nights,
        total_price=order.total_price,
        status=order.status,
        guest_name=order.guest_name,
        guest_phone=order.guest_phone,
        remark=order.remark,
        cancel_reason=order.cancel_reason,
        paid_at=order.paid_at,
        cancelled_at=order.cancelled_at,
        created_at=order.created_at,
    )
