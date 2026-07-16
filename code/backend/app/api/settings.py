"""
伊家人酒店系统 - 系统设置 API
酒店信息 / 系统配置
"""
import os
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Hotel
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["系统设置"])

# ── JSON 持久化配置 ──────────────────────────────────
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "hotel_settings.json")

DEFAULT_SETTINGS = {
    "hotel_name": "",
    "hotel_phone": "",
    "hotel_address": "",
    "checkin_time": "14:00",
    "checkout_time": "12:00",
    "currency": "CNY",
    "tax_rate": 6.0,
}


def _load_settings() -> dict:
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(saved)
            return merged
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()


def _save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Schemas ──────────────────────────────────────────

class HotelInfoOut(BaseModel):
    id: int
    name: str
    address: str
    phone: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None


class SettingsOut(BaseModel):
    hotel_info: Optional[HotelInfoOut] = None
    system_config: dict


class SettingsUpdate(BaseModel):
    hotel_name: Optional[str] = None
    hotel_phone: Optional[str] = None
    hotel_address: Optional[str] = None
    checkin_time: Optional[str] = None
    checkout_time: Optional[str] = None
    currency: Optional[str] = None
    tax_rate: Optional[float] = None


# ── 路由 ─────────────────────────────────────────────

@router.get("", response_model=SettingsOut, summary="获取系统设置")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取酒店信息和系统配置"""
    system_config = _load_settings()

    # 取默认酒店信息
    hotel = None
    default_hotel_id = system_config.get("default_hotel_id")
    if default_hotel_id:
        result = await db.execute(select(Hotel).where(Hotel.id == default_hotel_id))
        hotel = result.scalar_one_or_none()

    if not hotel:
        result = await db.execute(select(Hotel).where(Hotel.is_active == True).limit(1))
        hotel = result.scalar_one_or_none()

    hotel_info = None
    if hotel:
        hotel_info = HotelInfoOut(
            id=hotel.id,
            name=hotel.name,
            address=hotel.address,
            phone=hotel.phone,
            city=hotel.city,
            description=hotel.description,
        )

    return SettingsOut(hotel_info=hotel_info, system_config=system_config)


@router.put("", response_model=SettingsOut, summary="更新系统设置")
async def update_settings(
    req: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新酒店信息和系统配置"""
    current = _load_settings()
    update_data = req.model_dump(exclude_unset=True)
    current.update(update_data)
    _save_settings(current)

    # 重新组装返回
    return await get_settings(db, current_user)
