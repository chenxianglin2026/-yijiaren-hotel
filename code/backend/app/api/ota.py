"""
OTA 渠道对接模块 — 携程/美团/飞猪房态同步

功能：
- 渠道管理（添加/编辑/启用/停用 API 凭证）
- 房态自动同步（可用房数/价格推送到 OTA）
- 渠道订单回调接收 → 自动创建本地订单
- 订单状态反向同步（本地状态变更推送回 OTA）
"""
import json
import hmac
import hashlib
import time
import logging
from datetime import datetime, date
from typing import Optional, List, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db, User, Hotel, Room, Order, Checkin, OTAChannel, OTAOrderMapping
from app.db import OrderStatus, CheckinStatus
from app.api.auth import get_current_user, hash_password
from app.config import settings

logger = logging.getLogger("ota")
router = APIRouter(prefix="/api/ota", tags=["OTA对接"])


# ═══════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════

class ChannelConfigCreate(BaseModel):
    channel: str = Field(..., description="渠道ID: ctrip / meituan / fliggy")
    name: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    hotel_mapping: Optional[Dict[int, str]] = None  # {local_hotel_id: ota_hotel_id}
    sync_interval: int = 300


class ChannelConfigUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    hotel_mapping: Optional[Dict[int, str]] = None
    is_enabled: Optional[bool] = None
    sync_interval: Optional[int] = None


class RoomAvailability(BaseModel):
    room_id: int
    date: str
    available: int
    price: float


class SyncRequest(BaseModel):
    hotel_id: int
    channel: str
    rooms: List[RoomAvailability]


class OTAOrderPayload(BaseModel):
    """OTA 渠道推送的订单数据结构"""
    ota_order_id: str
    hotel_id: int
    room_id: int
    room_count: int = 1
    checkin_date: str
    checkout_date: str
    total_price: float
    guest_name: str
    guest_phone: str
    remark: Optional[str] = None


class OTAResponse(BaseModel):
    code: int = 0
    data: Optional[dict] = None
    msg: str = "ok"


# ═══════════════════════════════════════════════════════════════
# 渠道列表（跨 OTA 通用的接口端点 — 占位，审核通过后替换真实地址）
# ═══════════════════════════════════════════════════════════════

CHANNEL_META = {
    "ctrip": {
        "name": "携程",
        "base_url": "https://api.ctrip.com/hotel/v2",
        "availability_url": "/availability",
        "order_url": "/order",
        "cancel_url": "/order/cancel",
    },
    "meituan": {
        "name": "美团",
        "base_url": "https://api.meituan.com/hotel",
        "availability_url": "/room/update",
        "order_url": "/order/receive",
        "cancel_url": "/order/cancel",
    },
    "fliggy": {
        "name": "飞猪",
        "base_url": "https://api.fliggy.com/hotel",
        "availability_url": "/inventory",
        "order_url": "/order",
        "cancel_url": "/order/cancel",
    },
}


def _sign_ctrip(params: dict, secret: str) -> str:
    """携程签名算法（占位 — 审核通过后替换真实算法）"""
    sorted_keys = sorted(params.keys())
    raw = "&".join(f"{k}={params[k]}" for k in sorted_keys) + secret
    return hashlib.md5(raw.encode()).hexdigest().upper()


def _sign_generic(params: dict, secret: str) -> str:
    """通用 HMAC-SHA256 签名"""
    raw = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


# ═══════════════════════════════════════════════════════════════
# 渠道管理 API
# ═══════════════════════════════════════════════════════════════

@router.get("/channels", response_model=OTAResponse, summary="已对接渠道列表")
async def list_channels(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出所有 OTA 渠道及其状态"""
    result = await db.execute(select(OTAChannel))
    channels = result.scalars().all()

    data = []
    for ch in channels:
        meta = CHANNEL_META.get(ch.channel, {})
        data.append({
            "id": ch.id,
            "channel": ch.channel,
            "name": ch.name or meta.get("name", ch.channel),
            "is_enabled": ch.is_enabled,
            "api_key_set": bool(ch.api_key),
            "api_secret_set": bool(ch.api_secret),
            "hotel_mapping": json.loads(ch.hotel_mapping) if ch.hotel_mapping else {},
            "sync_interval": ch.sync_interval,
            "last_sync_at": ch.last_sync_at.isoformat() if ch.last_sync_at else None,
        })

    # 如果 DB 里还没有记录，返回默认列表
    if not data:
        data = [
            {"channel": cid, "name": meta["name"], "is_enabled": False,
             "api_key_set": False, "api_secret_set": False,
             "hotel_mapping": {}, "sync_interval": 300, "last_sync_at": None}
            for cid, meta in CHANNEL_META.items()
        ]

    return OTAResponse(data={"channels": data})


@router.post("/channels", response_model=OTAResponse, summary="添加/配置渠道")
async def create_channel(
    req: ChannelConfigCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """配置新的 OTA 渠道"""
    if req.channel not in CHANNEL_META:
        raise HTTPException(400, f"不支持的渠道: {req.channel}")

    # 检查是否已存在
    existing = await db.execute(
        select(OTAChannel).where(OTAChannel.channel == req.channel)
    )
    if existing.scalar():
        raise HTTPException(400, f"渠道 {req.channel} 已存在，请使用更新接口")

    mapping_json = json.dumps(req.hotel_mapping) if req.hotel_mapping else None
    channel = OTAChannel(
        channel=req.channel,
        name=req.name,
        api_key=req.api_key,
        api_secret=req.api_secret,
        hotel_mapping=mapping_json,
        sync_interval=req.sync_interval,
        is_enabled=True,
    )
    db.add(channel)
    await db.flush()
    return OTAResponse(data={"id": channel.id, "channel": req.channel}, msg="渠道配置成功")


@router.put("/channels/{channel}", response_model=OTAResponse, summary="更新渠道配置")
async def update_channel(
    channel: str,
    req: ChannelConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新 OTA 渠道配置"""
    result = await db.execute(
        select(OTAChannel).where(OTAChannel.channel == channel)
    )
    ch = result.scalar()
    if not ch:
        raise HTTPException(404, f"渠道 {channel} 不存在")

    if req.name is not None:
        ch.name = req.name
    if req.api_key is not None:
        ch.api_key = req.api_key
    if req.api_secret is not None:
        ch.api_secret = req.api_secret
    if req.hotel_mapping is not None:
        ch.hotel_mapping = json.dumps(req.hotel_mapping)
    if req.is_enabled is not None:
        ch.is_enabled = req.is_enabled
    if req.sync_interval is not None:
        ch.sync_interval = req.sync_interval

    await db.flush()
    return OTAResponse(msg=f"渠道 {channel} 更新成功")


@router.delete("/channels/{channel}", response_model=OTAResponse, summary="删除渠道")
async def delete_channel(
    channel: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OTAChannel).where(OTAChannel.channel == channel)
    )
    ch = result.scalar()
    if not ch:
        raise HTTPException(404, f"渠道 {channel} 不存在")

    await db.delete(ch)
    await db.flush()
    return OTAResponse(msg=f"渠道 {channel} 已删除")


# ═══════════════════════════════════════════════════════════════
# 房态同步 API
# ═══════════════════════════════════════════════════════════════

async def _do_sync_to_channel(
    ch: OTAChannel,
    hotel_id: int,
    rooms_data: List[dict],
) -> dict:
    """向单个 OTA 渠道推送房态（带签名和重试）"""
    if not ch.api_key or not ch.api_secret:
        return {"success": False, "error": "API 凭证未配置"}

    meta = CHANNEL_META.get(ch.channel, {})
    base_url = meta.get("base_url", "")
    url_path = meta.get("availability_url", "")
    if not base_url:
        return {"success": False, "error": f"未找到渠道 {ch.channel} 的 API 地址"}

    # 构建请求体
    ota_hotel_map = json.loads(ch.hotel_mapping) if ch.hotel_mapping else {}
    ota_hotel_id = ota_hotel_map.get(str(hotel_id), str(hotel_id))

    payload = {
        "hotel_id": ota_hotel_id,
        "timestamp": int(time.time()),
        "rooms": rooms_data,
    }

    # 签名
    if ch.channel == "ctrip":
        payload["sign"] = _sign_ctrip(payload, ch.api_secret)
    else:
        payload["sign"] = _sign_generic(payload, ch.api_secret)

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": ch.api_key,
    }

    # HTTP 推送 + 重试
    url = base_url.rstrip("/") + "/" + url_path.lstrip("/")
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    return {"success": True, "status": resp.status_code, "synced": len(rooms_data)}
                data = resp.json() if resp.text else {}
                if resp.status_code >= 500:
                    await _sleep_async(2 ** attempt)
                    continue
                return {"success": False, "error": f"OTA 返回 {resp.status_code}: {data.get('message', resp.text[:200])}"}
        except httpx.RequestError as e:
            if attempt < 2:
                await _sleep_async(2 ** attempt)
                continue
            return {"success": False, "error": str(e)[:500]}

    return {"success": False, "error": "重试耗尽"}


async def _sleep_async(seconds: float):
    """异步等待"""
    import asyncio
    await asyncio.sleep(seconds)


@router.post("/sync/availability", response_model=OTAResponse, summary="推送房态到渠道")
async def sync_availability(
    req: SyncRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """向 OTA 渠道推送实时房态和价格"""
    # 获取渠道配置
    result = await db.execute(
        select(OTAChannel).where(
            OTAChannel.channel == req.channel,
            OTAChannel.is_enabled == True,
        )
    )
    ch = result.scalar()
    if not ch:
        raise HTTPException(400, f"渠道 {req.channel} 未启用或未配置")

    # 构建推送数据
    rooms_data = [
        {"room_id": r.room_id, "date": r.date, "available": r.available, "price": r.price}
        for r in req.rooms
    ]

    # 后台异步推送，不阻塞用户请求
    background_tasks.add_task(_do_sync_to_channel, ch, req.hotel_id, rooms_data)

    return OTAResponse(
        data={"synced": len(rooms_data), "channel": req.channel},
        msg=f"正在向 {req.channel} 同步 {len(rooms_data)} 个房型",
    )


@router.post("/sync/auto", response_model=OTAResponse, summary="自动同步所有启用渠道")
async def auto_sync_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """自动同步所有酒店的最新房态到所有启用渠道（定时任务调用）"""
    # 获取所有启用渠道
    ch_result = await db.execute(
        select(OTAChannel).where(OTAChannel.is_enabled == True)
    )
    channels = ch_result.scalars().all()
    if not channels:
        return OTAResponse(msg="没有启用的渠道")

    # 获取所有活跃酒店的房间
    hotel_result = await db.execute(
        select(Hotel).where(Hotel.is_active == True).options(selectinload(Hotel.rooms))
    )
    hotels = hotel_result.scalars().all()

    results = {}
    today = date.today().isoformat()

    for ch in channels:
        ch_results = []
        for hotel in hotels:
            rooms_data = [
                {"room_id": r.id, "date": today, "available": r.available_count, "price": r.price}
                for r in hotel.rooms if r.is_active
            ]
            if rooms_data:
                r = await _do_sync_to_channel(ch, hotel.id, rooms_data)
                ch_results.append({"hotel_id": hotel.id, "rooms": len(rooms_data), **r})

        # 更新最后同步时间
        ch.last_sync_at = datetime.utcnow()
        results[ch.channel] = ch_results

    await db.flush()
    return OTAResponse(data={"results": results}, msg="自动同步完成")


# ═══════════════════════════════════════════════════════════════
# OTA 订单回调 → 创建本地订单
# ═══════════════════════════════════════════════════════════════

async def _create_order_from_ota(
    db: AsyncSession,
    payload: OTAOrderPayload,
    channel: str,
    raw_body: dict,
) -> Optional[Order]:
    """从 OTA 订单数据创建本地订单"""
    import uuid

    # 检查是否已存在（去重）
    existing = await db.execute(
        select(OTAOrderMapping).where(
            OTAOrderMapping.ota_order_id == payload.ota_order_id,
            OTAOrderMapping.channel == channel,
        )
    )
    if existing.scalar():
        logger.warning(f"OTA 订单 {payload.ota_order_id} 已存在，跳过")
        # 但仍返回关联的本地订单
        result = await db.execute(
            select(Order).join(OTAOrderMapping).where(
                OTAOrderMapping.ota_order_id == payload.ota_order_id
            )
        )
        return result.scalar()

    # 计算入住天数
    checkin = date.fromisoformat(payload.checkin_date)
    checkout = date.fromisoformat(payload.checkout_date)
    nights = (checkout - checkin).days
    if nights < 1:
        nights = 1

    # 查找或创建用户（以手机号为标识）
    result = await db.execute(
        select(User).where(User.phone == payload.guest_phone)
    )
    user = result.scalar()
    if not user:
        user = User(
            username=f"ota_{payload.guest_phone}",
            phone=payload.guest_phone,
            nickname=payload.guest_name,
            hashed_password=hash_password(f"ota_{payload.guest_phone}"),  # OTA 用户无需密码登录，用手机号+随机盐哈希
            role="guest",
        )
        db.add(user)
        await db.flush()

    # 创建订单
    order = Order(
        order_no=f"OTA-{channel[:2].upper()}-{uuid.uuid4().hex[:12].upper()}",
        user_id=user.id,
        hotel_id=payload.hotel_id,
        room_id=payload.room_id,
        room_count=payload.room_count,
        checkin_date=checkin,
        checkout_date=checkout,
        nights=nights,
        total_price=payload.total_price,
        status=OrderStatus.PAID,  # OTA 渠道订单默认已支付
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
        remark=f"[{channel}] {payload.remark or ''}".strip(),
    )
    db.add(order)
    await db.flush()

    # 减少可用房间数
    await db.execute(
        update(Room)
        .where(Room.id == payload.room_id)
        .values(available_count=Room.available_count - payload.room_count)
    )

    # 记录映射
    mapping = OTAOrderMapping(
        local_order_id=order.id,
        ota_order_id=payload.ota_order_id,
        channel=channel,
        raw_data=json.dumps(raw_body, ensure_ascii=False),
    )
    db.add(mapping)
    await db.flush()

    return order


@router.post("/webhook/{channel}", response_model=OTAResponse, summary="渠道订单回调")
async def ota_webhook(channel: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    接收 OTA 渠道推送的新订单。
    各 OTA 回调格式不同，根据 channel 适配解析。
    """
    if channel not in CHANNEL_META:
        raise HTTPException(400, f"不支持的渠道回调: {channel}")

    try:
        body = await request.json()
    except Exception:
        body = {}

    # 根据渠道解析不同格式
    if channel == "ctrip":
        payload = OTAOrderPayload(
            ota_order_id=body.get("OrderId", body.get("order_id", "")),
            hotel_id=int(body.get("HotelId", body.get("hotel_id", 0))),
            room_id=int(body.get("RoomId", body.get("room_id", 0))),
            room_count=int(body.get("RoomCount", body.get("room_count", 1))),
            checkin_date=body.get("CheckIn", body.get("checkin_date", "")),
            checkout_date=body.get("CheckOut", body.get("checkout_date", "")),
            total_price=float(body.get("TotalPrice", body.get("total_price", 0))),
            guest_name=body.get("ContactName", body.get("guest_name", "")),
            guest_phone=body.get("ContactPhone", body.get("guest_phone", "")),
            remark=body.get("Remark", body.get("remark")),
        )
    elif channel == "meituan":
        order_data = body.get("data", body)
        payload = OTAOrderPayload(
            ota_order_id=order_data.get("order_id", ""),
            hotel_id=int(order_data.get("hotel_id", 0)),
            room_id=int(order_data.get("room_id", 0)),
            room_count=int(order_data.get("num", 1)),
            checkin_date=order_data.get("check_in", ""),
            checkout_date=order_data.get("check_out", ""),
            total_price=float(order_data.get("total", 0)),
            guest_name=order_data.get("name", ""),
            guest_phone=order_data.get("mobile", ""),
            remark=order_data.get("remark"),
        )
    elif channel == "fliggy":
        payload = OTAOrderPayload(
            ota_order_id=body.get("tid", ""),
            hotel_id=int(body.get("hotel_id", 0)),
            room_id=int(body.get("rid", 0)),
            room_count=int(body.get("num", 1)),
            checkin_date=body.get("check_in", ""),
            checkout_date=body.get("check_out", ""),
            total_price=float(body.get("payment", 0)),
            guest_name=body.get("buyer_nick", ""),
            guest_phone=body.get("mobile", ""),
            remark=body.get("buyer_message"),
        )
    else:
        payload = OTAOrderPayload(**body)

    if not payload.ota_order_id:
        raise HTTPException(400, "缺少 ota_order_id")

    try:
        order = await _create_order_from_ota(db, payload, channel, body)
        if not order:
            raise HTTPException(500, "OTA 订单去重失败：映射存在但本地订单丢失")
        logger.info(f"OTA 订单已创建: {payload.ota_order_id} → 本地订单 {order.order_no}")
        return OTAResponse(
            data={"local_order_id": order.id, "local_order_no": order.order_no},
            msg=f"{channel} 订单 {payload.ota_order_id} 已接收",
        )
    except Exception as e:
        logger.exception(f"OTA 订单创建失败: {payload.ota_order_id}")
        raise HTTPException(500, f"订单创建失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# 订单状态反向同步
# ═══════════════════════════════════════════════════════════════

@router.post("/sync/order-status", response_model=OTAResponse, summary="反向同步订单状态到OTA")
async def sync_order_status_to_ota(
    order_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """本地订单状态变更后，推送回 OTA 渠道"""
    # 查找 OTA 映射
    result = await db.execute(
        select(OTAOrderMapping).where(OTAOrderMapping.local_order_id == order_id)
    )
    mapping = result.scalar()
    if not mapping:
        return OTAResponse(code=1, msg="该订单非 OTA 渠道订单")

    # 查找订单
    order_result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = order_result.scalar()
    if not order:
        raise HTTPException(404, "订单不存在")

    # 获取渠道配置
    ch_result = await db.execute(
        select(OTAChannel).where(OTAChannel.channel == mapping.channel)
    )
    ch = ch_result.scalar()
    if not ch or not ch.is_enabled:
        return OTAResponse(code=1, msg=f"渠道 {mapping.channel} 未启用")

    meta = CHANNEL_META.get(mapping.channel, {})
    base_url = meta.get("base_url", "")
    url_path = meta.get("cancel_url", "") if order.status == OrderStatus.CANCELLED else meta.get("order_url", "")

    payload = {
        "ota_order_id": mapping.ota_order_id,
        "status": order.status,
        "cancel_reason": order.cancel_reason,
        "timestamp": int(time.time()),
    }

    if ch.channel == "ctrip":
        payload["sign"] = _sign_ctrip(payload, ch.api_secret or "")
    else:
        payload["sign"] = _sign_generic(payload, ch.api_secret or "")

    async def _do_sync():
        url = base_url.rstrip("/") + "/" + url_path.lstrip("/")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json", "X-API-Key": ch.api_key or ""},
                )
                logger.info(f"OTA 订单状态同步: {mapping.ota_order_id} → {order.status} [{resp.status_code}]")
        except Exception as e:
            logger.error(f"OTA 订单状态同步失败: {mapping.ota_order_id}: {e}")

    background_tasks.add_task(_do_sync)
    return OTAResponse(msg=f"正在向 {mapping.channel} 同步订单 {order.order_no} 状态")
