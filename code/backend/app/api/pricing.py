"""
伊家人酒店系统 - 价格策略 API
规则管理 / 价格计算
"""
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, PricingRule, Room, Hotel, User, PricingRuleType, PricingAdjustType
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/pricing", tags=["价格策略"])


# ── Schemas ──────────────────────────────────────────
class PricingRuleCreate(BaseModel):
    hotel_id: int
    room_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    rule_type: str = Field(..., pattern=r"^(weekend|weekday|holiday|advance_booking|long_stay|seasonal)$")
    adjust_type: str = Field(..., pattern=r"^(percent|fixed|override)$")
    adjust_value: float
    priority: int = Field(0, description="数字越小优先级越高")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    weekdays: Optional[str] = None
    min_nights: Optional[int] = None
    max_advance_days: Optional[int] = None
    is_active: bool = True


class PricingRuleUpdate(BaseModel):
    hotel_id: Optional[int] = None
    room_id: Optional[int] = None
    name: Optional[str] = None
    rule_type: Optional[str] = None
    adjust_type: Optional[str] = None
    adjust_value: Optional[float] = None
    priority: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    weekdays: Optional[str] = None
    min_nights: Optional[int] = None
    max_advance_days: Optional[int] = None
    is_active: Optional[bool] = None


class PricingRuleOut(BaseModel):
    id: int
    hotel_id: int
    room_id: Optional[int] = None
    name: str
    rule_type: str
    adjust_type: str
    adjust_value: float
    priority: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    weekdays: Optional[str] = None
    min_nights: Optional[int] = None
    max_advance_days: Optional[int] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PricingRuleListResponse(BaseModel):
    total: int
    items: List[PricingRuleOut]


class PriceCalculationResult(BaseModel):
    base_price: float
    final_price: float
    applied_rules: List[dict]
    breakdown: List[dict]
    total: float


# ── 辅助: 检查管理员权限 ─────────────────────────────
def _require_admin(current_user: User):
    if current_user.role not in ("admin", "front_desk"):
        raise HTTPException(status_code=403, detail="仅管理员可管理价格策略")


# ── 辅助: 价格计算核心逻辑 ───────────────────────────
async def calculate_room_price(
    db: AsyncSession,
    room_id: int,
    checkin_date: date,
    checkout_date: date,
    booking_date: Optional[date] = None,
) -> dict:
    """
    计算某房型在指定日期范围的实际价格。
    返回每天的明细和总价。
    """
    if booking_date is None:
        booking_date = date.today()

    room_result = await db.execute(select(Room).where(Room.id == room_id))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房型不存在")

    nights = (checkout_date - checkin_date).days
    if nights < 1:
        raise HTTPException(status_code=400, detail="入住天数至少为1天")

    # 获取所有可能适用的活跃规则（room_id 为 null 或匹配）
    rules_result = await db.execute(
        select(PricingRule)
        .where(PricingRule.is_active == True)
        .where(
            (PricingRule.room_id.is_(None)) | (PricingRule.room_id == room_id)
        )
        .order_by(PricingRule.priority.asc())
    )
    all_rules = rules_result.scalars().all()

    breakdown = []
    total = 0.0
    all_applied_rules = []

    for offset in range(nights):
        day = checkin_date + timedelta(days=offset)
        day_price = float(room.price)
        day_applied = []

        for rule in all_rules:
            if _rule_matches(rule, day, nights, booking_date):
                old_price = day_price
                if rule.adjust_type == PricingAdjustType.PERCENT:
                    day_price = day_price * (1 + rule.adjust_value / 100.0)
                elif rule.adjust_type == PricingAdjustType.FIXED:
                    day_price = day_price + rule.adjust_value
                elif rule.adjust_type == PricingAdjustType.OVERRIDE:
                    day_price = rule.adjust_value

                day_applied.append({
                    "rule_id": rule.id,
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "adjust_type": rule.adjust_type,
                    "adjust_value": rule.adjust_value,
                    "priority": rule.priority,
                    "price_before": round(old_price, 2),
                    "price_after": round(day_price, 2),
                })
                if rule not in all_applied_rules:
                    all_applied_rules.append(rule)

        day_final = round(day_price, 2)
        total += day_final
        breakdown.append({
            "date": day.isoformat(),
            "base_price": float(room.price),
            "final_price": day_final,
            "applied_rules_count": len(day_applied),
        })

    # 去重并保持顺序
    seen_ids = set()
    unique_applied = []
    for r in all_applied_rules:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            unique_applied.append({
                "rule_id": r.id,
                "name": r.name,
                "rule_type": r.rule_type,
                "adjust_type": r.adjust_type,
                "adjust_value": r.adjust_value,
                "priority": r.priority,
            })

    return {
        "base_price": float(room.price),
        "final_price": round(total / nights, 2) if nights > 0 else 0,
        "applied_rules": unique_applied,
        "breakdown": breakdown,
        "total": round(total, 2),
    }


def _rule_matches(rule: PricingRule, day: date, nights: int, booking_date: date) -> bool:
    """判断单条规则是否匹配某一天"""
    # 日期范围
    if rule.start_date is not None and day < rule.start_date:
        return False
    if rule.end_date is not None and day > rule.end_date:
        return False

    # 星期几
    if rule.weekdays is not None and rule.weekdays.strip() != "":
        allowed = [int(w.strip()) for w in rule.weekdays.split(",") if w.strip() != ""]
        if day.weekday() not in allowed:
            return False

    # 最少住几晚
    if rule.min_nights is not None and nights < rule.min_nights:
        return False

    # 提前预订天数
    if rule.max_advance_days is not None:
        advance = (day - booking_date).days
        if advance < 0 or advance > rule.max_advance_days:
            return False

    return True


# ── 路由: 规则管理 ───────────────────────────────────
@router.get("/rules", response_model=PricingRuleListResponse, summary="查看所有价格规则")
async def list_pricing_rules(
    hotel_id: Optional[int] = Query(None),
    room_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    query = select(PricingRule)
    count_q = select(func.count(PricingRule.id))

    if hotel_id is not None:
        query = query.where(PricingRule.hotel_id == hotel_id)
        count_q = count_q.where(PricingRule.hotel_id == hotel_id)
    if room_id is not None:
        query = query.where(
            (PricingRule.room_id == room_id) | (PricingRule.room_id.is_(None))
        )
        count_q = count_q.where(
            (PricingRule.room_id == room_id) | (PricingRule.room_id.is_(None))
        )
    if is_active is not None:
        query = query.where(PricingRule.is_active == is_active)
        count_q = count_q.where(PricingRule.is_active == is_active)

    total_result = await db.execute(count_q)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(PricingRule.priority.asc(), PricingRule.created_at.desc())
        .offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return PricingRuleListResponse(
        total=total,
        items=[PricingRuleOut.model_validate(r) for r in items],
    )


@router.post("/rules", response_model=PricingRuleOut, status_code=201, summary="创建价格规则")
async def create_pricing_rule(
    req: PricingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    # 校验 hotel 存在
    hotel_result = await db.execute(select(Hotel).where(Hotel.id == req.hotel_id))
    if not hotel_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="门店不存在")

    # 校验 room 存在（如指定）
    if req.room_id is not None:
        room_result = await db.execute(select(Room).where(Room.id == req.room_id))
        if not room_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="房型不存在")

    rule = PricingRule(**req.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return PricingRuleOut.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=PricingRuleOut, summary="编辑价格规则")
async def update_pricing_rule(
    rule_id: int,
    req: PricingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(rule)
    return PricingRuleOut.model_validate(rule)


@router.delete("/rules/{rule_id}", summary="删除价格规则")
async def delete_pricing_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    await db.delete(rule)
    await db.flush()
    return {"code": 0, "msg": "删除成功"}


@router.get("/rules/{rule_id}/toggle", response_model=PricingRuleOut, summary="启用/停用规则")
async def toggle_pricing_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    rule.is_active = not rule.is_active
    rule.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(rule)
    return PricingRuleOut.model_validate(rule)


# ── 路由: 价格计算（公开） ───────────────────────────
@router.get("/calculate", summary="计算某房型某日期的实际价格")
async def calculate_price(
    room_id: int = Query(..., description="房型ID"),
    date_str: str = Query(..., alias="date", description="入住日期 YYYY-MM-DD"),
    nights: int = Query(1, ge=1, le=365, description="入住天数"),
    db: AsyncSession = Depends(get_db),
):
    try:
        checkin_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    checkout_date = checkin_date + timedelta(days=nights)
    result = await calculate_room_price(db, room_id, checkin_date, checkout_date)
    return {"code": 0, "data": result}
