"""
伊家人酒店系统 - 财务报表 API
日营收 / 月营收 / 支付对账
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Hotel, Order, Checkin, OrderStatus, CheckinStatus
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/finance", tags=["财务管理"])


# ── Schemas ──────────────────────────────────────────

class DailyRevenueItem(BaseModel):
    date: str  # YYYY-MM-DD
    total_orders: int = 0  # 总订单数
    paid_orders: int = 0  # 已支付订单数
    revenue: float = 0.0  # 营收总额
    avg_order_value: float = 0.0  # 客单价


class DailyRevenueResponse(BaseModel):
    code: int = 0
    data: list[DailyRevenueItem]
    msg: str = "ok"
    summary: Optional[dict] = None  # 汇总统计


class MonthlyRevenueItem(BaseModel):
    year: int
    month: int
    total_orders: int = 0
    paid_orders: int = 0
    completed_orders: int = 0
    cancelled_orders: int = 0
    revenue: float = 0.0
    avg_order_value: float = 0.0


class MonthlyRevenueResponse(BaseModel):
    code: int = 0
    data: MonthlyRevenueItem
    msg: str = "ok"


class ReconciliationItem(BaseModel):
    """支付对账条目"""
    order_no: str
    hotel_name: str
    guest_name: str
    total_price: float
    status: str
    paid_at: Optional[str] = None
    created_at: str
    checkin_date: str
    checkout_date: str


class ReconciliationResponse(BaseModel):
    code: int = 0
    data: list[ReconciliationItem]
    msg: str = "ok"
    summary: Optional[dict] = None  # { total_count, total_amount, paid_count, paid_amount, pending_count, ... }


# ── 辅助函数 ─────────────────────────────────────────
def _parse_date_range(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    """解析日期范围字符串"""
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d")
        ed = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    if sd > ed:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    # end_date 包含当天，所以加一天
    return sd, ed + timedelta(days=1)


# ── 路由 ─────────────────────────────────────────────

@router.get("/daily", response_model=DailyRevenueResponse, summary="日营收报表")
async def daily_revenue(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    hotel_id: Optional[int] = Query(None, description="门店ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询指定日期范围内的每日营收统计。
    返回每天的订单数、已支付订单数、营收额、客单价。
    """
    sd, ed = _parse_date_range(start_date, end_date)

    # 构建查询条件
    conditions = [
        Order.created_at >= sd,
        Order.created_at < ed,
    ]
    if hotel_id:
        conditions.append(Order.hotel_id == hotel_id)

    # 查询所有符合条件的订单
    result = await db.execute(
        select(Order).where(*conditions).order_by(Order.created_at.asc())
    )
    orders = result.scalars().all()

    # 按天聚合
    daily_map: dict[str, dict] = {}
    # 初始化日期范围
    current = sd
    while current < ed:
        day_str = current.strftime("%Y-%m-%d")
        daily_map[day_str] = {
            "total_orders": 0,
            "paid_orders": 0,
            "revenue": 0.0,
        }
        current += timedelta(days=1)

    for o in orders:
        day_str = o.created_at.strftime("%Y-%m-%d")
        if day_str not in daily_map:
            daily_map[day_str] = {"total_orders": 0, "paid_orders": 0, "revenue": 0.0}
        daily_map[day_str]["total_orders"] += 1
        if o.status in (OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED):
            daily_map[day_str]["paid_orders"] += 1
            daily_map[day_str]["revenue"] += o.total_price

    items = []
    total_revenue = 0.0
    total_paid = 0
    total_all = 0
    for day_str in sorted(daily_map.keys()):
        d = daily_map[day_str]
        total_revenue += d["revenue"]
        total_paid += d["paid_orders"]
        total_all += d["total_orders"]
        items.append(DailyRevenueItem(
            date=day_str,
            total_orders=d["total_orders"],
            paid_orders=d["paid_orders"],
            revenue=round(d["revenue"], 2),
            avg_order_value=round(d["revenue"] / d["paid_orders"], 2) if d["paid_orders"] > 0 else 0.0,
        ))

    summary = {
        "total_revenue": round(total_revenue, 2),
        "total_paid_orders": total_paid,
        "total_orders": total_all,
        "avg_order_value": round(total_revenue / total_paid, 2) if total_paid > 0 else 0.0,
    }

    return DailyRevenueResponse(data=items, msg="ok", summary=summary)


@router.get("/monthly", response_model=MonthlyRevenueResponse, summary="月营收报表")
async def monthly_revenue(
    year: int = Query(..., ge=2020, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    hotel_id: Optional[int] = Query(None, description="门店ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询指定月份的营收汇总统计。
    """
    from calendar import monthrange

    # 计算月份起止时间
    start_dt = datetime(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    end_dt = datetime(year, month, days_in_month) + timedelta(days=1)

    conditions = [
        Order.created_at >= start_dt,
        Order.created_at < end_dt,
    ]
    if hotel_id:
        conditions.append(Order.hotel_id == hotel_id)

    # 总订单数
    total_result = await db.execute(
        select(func.count(Order.id)).where(*conditions)
    )
    total_orders = total_result.scalar() or 0

    # 各状态订单数
    def make_status_cond(status):
        conds = list(conditions) + [Order.status == status]
        return conds

    paid_result = await db.execute(
        select(func.count(Order.id)).where(*make_status_cond(OrderStatus.PAID))
    )
    paid_orders = paid_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count(Order.id)).where(*make_status_cond(OrderStatus.COMPLETED))
    )
    completed_orders = completed_result.scalar() or 0

    # 已入住也算有效营收
    ckd_in_result = await db.execute(
        select(func.count(Order.id)).where(*make_status_cond(OrderStatus.CHECKED_IN))
    )
    ckd_in_orders = ckd_in_result.scalar() or 0

    cancelled_result = await db.execute(
        select(func.count(Order.id)).where(*make_status_cond(OrderStatus.CANCELLED))
    )
    cancelled_orders = cancelled_result.scalar() or 0

    # 营收总额（已支付 + 已入住 + 已完成）
    revenue_conditions = list(conditions) + [
        Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED])
    ]
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(*revenue_conditions)
    )
    revenue = round(float(revenue_result.scalar() or 0), 2)

    effective_paid = paid_orders + ckd_in_orders + completed_orders

    return MonthlyRevenueResponse(
        data=MonthlyRevenueItem(
            year=year,
            month=month,
            total_orders=total_orders,
            paid_orders=paid_orders + ckd_in_orders + completed_orders,
            completed_orders=completed_orders,
            cancelled_orders=cancelled_orders,
            revenue=revenue,
            avg_order_value=round(revenue / effective_paid, 2) if effective_paid > 0 else 0.0,
        ),
        msg="ok",
    )


@router.get("/reconciliation", response_model=ReconciliationResponse, summary="支付对账报表")
async def payment_reconciliation(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    hotel_id: Optional[int] = Query(None, description="门店ID"),
    status: Optional[str] = Query(None, description="订单状态筛选: paid/checked_in/completed/pending/cancelled"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    支付对账报表：列出指定日期范围内的所有订单及其支付状态。
    便于与支付平台（微信/支付宝）对账。
    """
    sd, ed = _parse_date_range(start_date, end_date)

    conditions = [
        Order.created_at >= sd,
        Order.created_at < ed,
    ]
    if hotel_id:
        conditions.append(Order.hotel_id == hotel_id)
    if status:
        conditions.append(Order.status == status)

    result = await db.execute(
        select(Order).where(*conditions).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    # 获取酒店名称映射
    all_hotel_ids = set(o.hotel_id for o in orders)
    hotel_map = {}
    if all_hotel_ids:
        hotels_result = await db.execute(
            select(Hotel).where(Hotel.id.in_(all_hotel_ids))
        )
        for h in hotels_result.scalars().all():
            hotel_map[h.id] = h.name

    items = []
    total_amount = 0.0
    paid_count = 0
    paid_amount = 0.0
    pending_count = 0
    pending_amount = 0.0
    cancelled_count = 0
    cancelled_amount = 0.0

    for o in orders:
        total_amount += o.total_price
        if o.status in (OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED):
            paid_count += 1
            paid_amount += o.total_price
        elif o.status == OrderStatus.PENDING:
            pending_count += 1
            pending_amount += o.total_price
        elif o.status == OrderStatus.CANCELLED:
            cancelled_count += 1
            cancelled_amount += o.total_price

        items.append(ReconciliationItem(
            order_no=o.order_no,
            hotel_name=hotel_map.get(o.hotel_id, f"门店#{o.hotel_id}"),
            guest_name=o.guest_name,
            total_price=o.total_price,
            status=o.status,
            paid_at=o.paid_at.isoformat() if o.paid_at else None,
            created_at=o.created_at.isoformat(),
            checkin_date=o.checkin_date.isoformat(),
            checkout_date=o.checkout_date.isoformat(),
        ))

    summary = {
        "total_count": len(orders),
        "total_amount": round(total_amount, 2),
        "paid_count": paid_count,
        "paid_amount": round(paid_amount, 2),
        "pending_count": pending_count,
        "pending_amount": round(pending_amount, 2),
        "cancelled_count": cancelled_count,
        "cancelled_amount": round(cancelled_amount, 2),
        "date_range": f"{start_date} ~ {end_date}",
    }

    return ReconciliationResponse(data=items, msg="ok", summary=summary)


@router.get("/overview", summary="财务总览")
async def finance_overview(
    hotel_id: Optional[int] = Query(None, description="门店ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    财务总览：今日/本月/累计营收
    """
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = today_start + timedelta(days=1)

    month_start = datetime(today.year, today.month, 1)
    days_in_month = 30  # 简化
    month_end = today_end  # 到今天

    def add_hotel_filter(conds):
        if hotel_id:
            conds.append(Order.hotel_id == hotel_id)
        return conds

    # 今日营收
    today_conds = add_hotel_filter([
        Order.created_at >= today_start,
        Order.created_at < today_end,
        Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
    ])
    today_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(*today_conds)
    )
    today_revenue = round(float(today_revenue_result.scalar() or 0), 2)

    # 今日订单数
    today_orders_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.created_at >= today_start,
            Order.created_at < today_end,
        )
    )
    today_orders = today_orders_result.scalar() or 0

    # 本月营收
    month_conds = add_hotel_filter([
        Order.created_at >= month_start,
        Order.created_at < month_end,
        Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
    ])
    month_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(*month_conds)
    )
    month_revenue = round(float(month_revenue_result.scalar() or 0), 2)

    # 本月订单数
    month_orders_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.created_at >= month_start,
            Order.created_at < month_end,
        )
    )
    month_orders = month_orders_result.scalar() or 0

    # 累计营收 (all time)
    total_conds = add_hotel_filter([
        Order.status.in_([OrderStatus.PAID, OrderStatus.CHECKED_IN, OrderStatus.COMPLETED]),
    ])
    total_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(*total_conds)
    )
    total_revenue = round(float(total_revenue_result.scalar() or 0), 2)

    # 累计订单数
    total_orders_result = await db.execute(
        select(func.count(Order.id))
    )
    total_orders = total_orders_result.scalar() or 0

    # 当前入住数
    ckd_conds = []
    if hotel_id:
        ckd_conds.append(Checkin.hotel_id == hotel_id)
    ckd_conds.append(Checkin.status == CheckinStatus.CHECKED_IN)
    ckd_result = await db.execute(
        select(func.count(Checkin.id)).where(*ckd_conds)
    )
    ckd_count = ckd_result.scalar() or 0

    return {
        "code": 0,
        "data": {
            "today": {
                "date": today.isoformat(),
                "revenue": today_revenue,
                "orders": today_orders,
            },
            "this_month": {
                "year": today.year,
                "month": today.month,
                "revenue": month_revenue,
                "orders": month_orders,
            },
            "total": {
                "revenue": total_revenue,
                "orders": total_orders,
            },
            "current_checkins": ckd_count,
        },
        "msg": "ok",
    }
