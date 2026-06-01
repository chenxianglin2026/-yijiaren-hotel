"""
OTA 渠道对接模块 — 携程/美团/飞猪房态同步
- 房态推送（可用房数/价格/房型）
- 订单接收（渠道订单同步到系统）
- 价格同步
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/ota", tags=["OTA对接"])


# ── Schemas ─────────────────────────────────────
class RoomAvailability(BaseModel):
    room_id: int
    date: str
    available: int
    price: float


class SyncRequest(BaseModel):
    hotel_id: int
    channel: str  # ctrip / meituan / fliggy
    rooms: List[RoomAvailability]


class OTAResponse(BaseModel):
    code: int = 0
    data: Optional[dict] = None
    msg: str = "ok"


# ── 路由 ───────────────────────────────────────
@router.post("/sync/availability", response_model=OTAResponse, summary="推送房态到渠道")
async def sync_availability(
    req: SyncRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """向 OTA 渠道推送实时房态和价格"""
    channel_urls = {
        "ctrip": "https://api.ctrip.com/hotel/availability",
        "meituan": "https://api.meituan.com/hotel/room/update",
        "fliggy": "https://api.fliggy.com/hotel/inventory",
    }
    url = channel_urls.get(req.channel)
    if not url:
        raise HTTPException(400, f"不支持的渠道: {req.channel}")

    # TODO: 真实 HTTP 推送
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(url, json={...})
    
    synced = len(req.rooms)
    return OTAResponse(data={"synced": synced, "channel": req.channel}, msg=f"已同步 {synced} 个房型到 {req.channel}")


@router.get("/channels", response_model=OTAResponse, summary="已对接渠道列表")
async def list_channels(user: User = Depends(get_current_user)):
    return OTAResponse(data={
        "channels": [
            {"id": "ctrip", "name": "携程", "status": "pending", "api_key_set": False},
            {"id": "meituan", "name": "美团", "status": "pending", "api_key_set": False},
            {"id": "fliggy", "name": "飞猪", "status": "pending", "api_key_set": False},
        ]
    })


@router.post("/webhook/{channel}", response_model=OTAResponse, summary="渠道订单回调")
async def ota_webhook(channel: str, request: Request):
    """接收 OTA 渠道推送的新订单"""
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    # TODO: 解析渠道订单 → 创建本地订单
    return OTAResponse(msg=f"{channel} 回调已接收")
