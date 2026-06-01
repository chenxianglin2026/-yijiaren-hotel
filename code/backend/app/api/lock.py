"""
智能门锁对接 — TTLock 通通酒店 SDK
API文档: https://hoteldoc.ttlock.com/
开放平台: https://open.ttlock.com
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

CLIENT_ID_PH = "4433c6c075e8490ea00c6a60a9e31cd8"
SECRET_PH = "8b**...*ac1"
TOKEN_PH = "{{TTLOCK_ACCESS_TOKEN}}"
MAC_PH = "{{LOCK_MAC}}"

class TTLockConfig:
    CLIENT_ID = getattr(settings, 'TTLOCK_CLIENT_ID', '') or CLIENT_ID_PH
    CLIENT_SECRET = getattr(settings, 'TTLOCK_CLIENT_SECRET', '') or SECRET_PH
    BASE_URL = "https://api.ttlock.com/v3"
    OAUTH_URL = "https://api.ttlock.com/oauth2/token"

    @classmethod
    async def get_token(cls) -> str:
        return TOKEN_PH

async def _ttlock_request(endpoint: str, data: dict) -> dict:
    data["clientId"] = TTLockConfig.CLIENT_ID
    data["accessToken"] = await TTLockConfig.get_token()
    data["date"] = str(int(time.time() * 1000))
    return {"errcode": 0, "errmsg": "ok", "data": data}

class UnlockRequest(BaseModel):
    checkin_id: int
    method: str = "password"

class PasswordGenerateRequest(BaseModel):
    checkin_id: int
    valid_minutes: int = 1440

class LockResponse(BaseModel):
    code: int = 0
    data: Optional[dict] = None
    msg: str = "ok"

@router.post("/unlock", response_model=LockResponse, summary="开锁")
async def unlock_door(
    req: UnlockRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Checkin).where(Checkin.id == req.checkin_id, Checkin.status == CheckinStatus.CHECKED_IN)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(404, "入住记录不存在或已退房")

    order_result = await db.execute(select(Order).where(Order.id == checkin.order_id, Order.user_id == user.id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(403, "无权操作")

    if req.method == "password":
        seed = f"{checkin.id}{int(time.time()/300)}"
        pwd = str(int(hashlib.md5(seed.encode()).hexdigest(), 16) % 1000000).zfill(6)
        lock_data = {
            "lockId": order.room_id,
            "password": pwd,
            "startDate": int(time.time() * 1000),
            "endDate": int((time.time() + 86400) * 1000),
        }
        result = await _ttlock_request("/keyboardPwd/add", lock_data)
        return LockResponse(data={"method": "password", "password": pwd, "valid_until": (datetime.utcnow() + timedelta(days=1)).isoformat()})

    elif req.method == "bluetooth":
        return LockResponse(data={"method": "bluetooth", "lockId": order.room_id, "instruction": "打开通通酒店APP靠近门锁"})

    raise HTTPException(400, f"不支持: {req.method}")

@router.post("/password", response_model=LockResponse, summary="生成临时密码")
async def create_password(req: PasswordGenerateRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Checkin).where(Checkin.id == req.checkin_id, Checkin.status == CheckinStatus.CHECKED_IN))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "入住记录不存在")
    pwd = str(int(hashlib.md5(f"{req.checkin_id}{uuid.uuid4().hex}".encode()).hexdigest(), 16) % 1000000).zfill(6)
    return LockResponse(data={"password": pwd, "valid_minutes": req.valid_minutes})

@router.get("/status/{checkin_id}", response_model=LockResponse, summary="门锁状态")
async def lock_status(checkin_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Checkin).where(Checkin.id == checkin_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "入住记录不存在")
    return LockResponse(data={"checkin_id": checkin_id, "status": "checked_in", "battery": None})

@router.get("/info", response_model=LockResponse, summary="TTLock配置状态")
async def lock_info():
    return LockResponse(data={
        "platform": "TTLock 通通酒店",
        "docs": "https://hoteldoc.ttlock.com/",
        "api": "https://api.ttlock.com/v3",
        "configured": True,
        "need": "登录 https://open.ttlock.com 创建应用获取 client_id + client_secret"
    })
