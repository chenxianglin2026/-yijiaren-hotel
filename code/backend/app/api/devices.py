"""设备监控 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/devices", tags=["设备监控"])

@router.get("/list")
async def list_devices(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return {"code": 0, "data": [], "msg": "ok"}
