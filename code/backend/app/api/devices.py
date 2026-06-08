"""
设备管理 API - 智能门锁、客控面板、传感器等物联网设备
支持设备注册、状态上报、列表查询、实时状态刷新
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Device, Hotel, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


# ── Schemas ──────────────────────────────────────────

class DeviceCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100, description="设备唯一ID")
    name: str = Field(..., min_length=1, max_length=200, description="设备名称")
    device_type: str = Field("smart_lock", description="smart_lock/control_panel/sensor/gateway/charger")
    hotel_id: Optional[int] = None
    room_number: Optional[str] = Field(None, max_length=20)
    ip_address: Optional[str] = Field(None, max_length=50)
    firmware_version: Optional[str] = Field(None, max_length=50)
    extra: Optional[str] = None


class DeviceStatusReport(BaseModel):
    """设备心跳/状态上报"""
    device_id: str = Field(..., description="设备唯一ID")
    status: str = Field("online", description="online/offline/alert")
    battery: Optional[int] = Field(None, ge=0, le=100, description="电量百分比")
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    extra: Optional[str] = None


class DeviceOut(BaseModel):
    id: int
    device_id: str
    name: str
    device_type: str
    hotel_id: Optional[int] = None
    hotel_name: Optional[str] = None
    room_number: Optional[str] = None
    status: str
    battery: Optional[int] = None
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    last_online: Optional[str] = None
    extra: Optional[str] = None
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class DeviceListResponse(BaseModel):
    code: int = 0
    data: list = []
    total: int = 0
    online_count: int = 0
    offline_count: int = 0
    alert_count: int = 0
    msg: str = "ok"


class DeviceDetailResponse(BaseModel):
    code: int = 0
    data: Optional[dict] = None
    msg: str = "ok"


# ── Helper ───────────────────────────────────────────

async def _get_hotel_name(db: AsyncSession, hotel_id: Optional[int]) -> Optional[str]:
    if not hotel_id:
        return None
    result = await db.execute(select(Hotel.name).where(Hotel.id == hotel_id))
    return result.scalar()


def _format_device(d: Device, hotel_name: Optional[str] = None) -> dict:
    return {
        "id": d.id,
        "device_id": d.device_id,
        "name": d.name,
        "device_type": d.device_type,
        "hotel_id": d.hotel_id,
        "hotel_name": hotel_name,
        "room_number": d.room_number,
        "status": d.status,
        "battery": d.battery,
        "firmware_version": d.firmware_version,
        "ip_address": d.ip_address,
        "last_online": d.last_online.isoformat() if d.last_online else None,
        "extra": d.extra,
        "enabled": d.enabled,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


# ── API Endpoints ────────────────────────────────────

@router.get("/list", response_model=DeviceListResponse, summary="设备列表")
async def list_devices(
    hotel_id: Optional[int] = Query(None, description="按门店筛选"),
    device_type: Optional[str] = Query(None, description="按类型筛选"),
    status: Optional[str] = Query(None, description="按状态筛选 online/offline/alert"),
    keyword: Optional[str] = Query(None, description="搜索设备名/ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有设备列表，支持筛选"""
    query = select(Device).where(Device.enabled == True)

    if hotel_id is not None:
        query = query.where(Device.hotel_id == hotel_id)
    if device_type:
        query = query.where(Device.device_type == device_type)
    if status:
        query = query.where(Device.status == status)
    if keyword:
        query = query.where(
            (Device.name.contains(keyword)) | (Device.device_id.contains(keyword))
        )

    query = query.order_by(Device.updated_at.desc())

    result = await db.execute(query)
    devices = result.scalars().all()

    # 统计
    online_count = sum(1 for d in devices if d.status == "online")
    offline_count = sum(1 for d in devices if d.status == "offline")
    alert_count = sum(1 for d in devices if d.status == "alert")

    # 批量获取酒店名（去重）
    hotel_ids = list(set(d.hotel_id for d in devices if d.hotel_id))
    hotel_map = {}
    if hotel_ids:
        hotel_result = await db.execute(
            select(Hotel.id, Hotel.name).where(Hotel.id.in_(hotel_ids))
        )
        for hid, hname in hotel_result:
            hotel_map[hid] = hname

    items = [_format_device(d, hotel_map.get(d.hotel_id)) for d in devices]

    return DeviceListResponse(
        data=items,
        total=len(items),
        online_count=online_count,
        offline_count=offline_count,
        alert_count=alert_count,
    )


@router.get("/stats", summary="设备统计概览")
async def device_stats(
    hotel_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设备统计：在线/离线/告警数量、低电量设备数"""
    base_q = select(Device).where(Device.enabled == True)
    if hotel_id:
        base_q = base_q.where(Device.hotel_id == hotel_id)

    result = await db.execute(base_q)
    devices = result.scalars().all()

    online = sum(1 for d in devices if d.status == "online")
    offline = sum(1 for d in devices if d.status == "offline")
    alert = sum(1 for d in devices if d.status == "alert")
    low_battery = sum(1 for d in devices if d.battery is not None and d.battery < 20)

    return {
        "code": 0,
        "data": {
            "total": len(devices),
            "online": online,
            "offline": offline,
            "alert": alert,
            "low_battery": low_battery,
        },
    }


@router.post("/register", response_model=DeviceDetailResponse, summary="注册设备")
async def register_device(
    req: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """注册新设备到系统"""
    if current_user.role not in ("admin", "front_desk"):
        raise HTTPException(status_code=403, detail="仅管理员/前台可注册设备")

    # 检查设备ID是否已存在
    existing = await db.execute(select(Device).where(Device.device_id == req.device_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"设备ID {req.device_id} 已存在")

    device = Device(
        device_id=req.device_id,
        name=req.name,
        device_type=req.device_type,
        hotel_id=req.hotel_id,
        room_number=req.room_number,
        ip_address=req.ip_address,
        firmware_version=req.firmware_version,
        extra=req.extra,
        status="offline",
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)

    hotel_name = await _get_hotel_name(db, device.hotel_id)

    return DeviceDetailResponse(
        data=_format_device(device, hotel_name),
        msg="设备注册成功",
    )


@router.post("/heartbeat", response_model=DeviceDetailResponse, summary="设备心跳上报")
async def device_heartbeat(
    req: DeviceStatusReport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设备定时上报心跳，更新在线状态、电量等信息"""
    result = await db.execute(select(Device).where(Device.device_id == req.device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail=f"设备 {req.device_id} 未注册")

    # 更新状态
    device.status = req.status
    if req.battery is not None:
        device.battery = req.battery
    if req.firmware_version is not None:
        device.firmware_version = req.firmware_version
    if req.ip_address is not None:
        device.ip_address = req.ip_address
    if req.extra is not None:
        device.extra = req.extra

    if req.status == "online":
        device.last_online = datetime.utcnow()

    device.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(device)

    hotel_name = await _get_hotel_name(db, device.hotel_id)

    return DeviceDetailResponse(
        data=_format_device(device, hotel_name),
        msg="心跳上报成功",
    )


@router.get("/{device_id}", response_model=DeviceDetailResponse, summary="设备详情")
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据设备ID获取设备详情"""
    result = await db.execute(
        select(Device).where(
            (Device.device_id == device_id) | (Device.id == (int(device_id) if device_id.isdigit() else 0))
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail=f"设备 {device_id} 不存在")

    hotel_name = await _get_hotel_name(db, device.hotel_id)

    return DeviceDetailResponse(data=_format_device(device, hotel_name))


@router.delete("/{device_id_str}", summary="删除设备")
async def delete_device(
    device_id_str: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """软删除设备（设置 enabled=False）"""
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="仅管理员可删除设备")

    result = await db.execute(select(Device).where(Device.device_id == device_id_str))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail=f"设备 {device_id_str} 不存在")

    device.enabled = False
    device.updated_at = datetime.utcnow()
    await db.flush()

    return {"code": 0, "msg": f"设备 {device.name} 已删除"}
