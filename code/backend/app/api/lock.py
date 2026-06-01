"""
智能门锁对接模块 — 锁掌智慧酒店门锁 SDK
支持: 蓝牙开锁 / 临时密码 / 远程开门 / 门锁状态查询
"""
import hashlib, time, uuid, json
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Order, Checkin, CheckinStatus
from app.api.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/lock", tags=["智能门锁"])


# ── 锁掌 SDK 配置 ───────────────────────────────
class LockConfig:
    APP_KEY = settings.LOCK_APP_KEY or "{{LOCK_APP_KEY}}"
    APP_SECRET = settings.LOCK_APP_SECRET or "{{LOCK_APP_SECRET}}"
    BASE_URL = settings.LOCK_BASE_URL or "https://api.suozhang.com/v1"


# ── Schemas ─────────────────────────────────────
class UnlockRequest(BaseModel):
    checkin_id: int
    method: str = "bluetooth"  # bluetooth / password / remote


class PasswordRequest(BaseModel):
    checkin_id: int
    valid_minutes: int = 1440  # 密码有效期（分钟），默认24小时


class LockResponse(BaseModel):
    code: int = 0
    data: Optional[dict] = None
    msg: str = "ok"


# ── 工具函数 ────────────────────────────────────
def _sign(params: dict) -> str:
    """锁掌 API 签名"""
    sorted_keys = sorted(params.keys())
    sign_str = "&".join(f"{k}={params[k]}" for k in sorted_keys)
    sign_str += f"&key={LockConfig.APP_SECRET}"
    return hashlib.md5(sign_str.encode()).hexdigest().upper()


def _generate_password(checkin_id: int, room_no: str, valid_minutes: int) -> str:
    """生成临时密码（6位数字）"""
    seed = f"{checkin_id}{room_no}{int(time.time()/300)}"
    return str(int(hashlib.md5(seed.encode()).hexdigest(), 16) % 1000000).zfill(6)


# ── 路由 ───────────────────────────────────────
@router.post("/unlock", response_model=LockResponse, summary="开锁（蓝牙/密码/远程）")
async def unlock_door(
    req: UnlockRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """通过入住记录开锁"""
    result = await db.execute(
        select(Checkin).where(Checkin.id == req.checkin_id, Checkin.status == CheckinStatus.CHECKED_IN)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(404, "入住记录不存在或已退房")

    # 获取订单和房间信息
    order_result = await db.execute(select(Order).where(Order.id == checkin.order_id, Order.user_id == user.id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(403, "无权操作")

    if req.method == "bluetooth":
        # 生成蓝牙开锁指令
        params = {
            "app_key": LockConfig.APP_KEY,
            "timestamp": str(int(time.time())),
            "nonce": uuid.uuid4().hex[:16],
            "room_no": str(order.room_id),
            "guest_id": str(user.id),
        }
        params["sign"] = _sign(params)
        
        return LockResponse(data={
            "method": "bluetooth",
            "instruction": json.dumps(params),
            "expires_in": 30
        })

    elif req.method == "password":
        pwd = _generate_password(checkin.id, str(order.room_id), 1440)
        return LockResponse(data={
            "method": "password",
            "password": pwd,
            "valid_until": (datetime.utcnow() + timedelta(minutes=1440)).isoformat()
        })

    else:
        raise HTTPException(400, f"不支持的开锁方式: {req.method}")


@router.post("/password", response_model=LockResponse, summary="生成临时密码")
async def create_password(
    req: PasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Checkin).where(Checkin.id == req.checkin_id, Checkin.status == CheckinStatus.CHECKED_IN)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(404, "入住记录不存在")

    pwd = _generate_password(checkin.id, str(checkin.order_id), req.valid_minutes)
    return LockResponse(data={
        "password": pwd,
        "valid_minutes": req.valid_minutes,
        "valid_until": (datetime.utcnow() + timedelta(minutes=req.valid_minutes)).isoformat()
    })


@router.get("/status/{checkin_id}", response_model=LockResponse, summary="门锁状态")
async def lock_status(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Checkin).where(Checkin.id == checkin_id))
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(404, "入住记录不存在")

    return LockResponse(data={
        "checkin_id": checkin_id,
        "status": checkin.status,
        "last_unlock": None,  # TODO: 记录最近一次开锁时间
        "battery": None,       # TODO: 锁具电量
    })
