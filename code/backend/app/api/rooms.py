"""
伊家人酒店系统 - 房态查询 API (最小版)
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/rooms", tags=["房态管理"])


@router.get("", summary="房间列表")
async def list_rooms():
    return {
        "code": 0,
        "msg": "ok",
        "items": [
            {"id": 1, "name": "标准大床房", "price": 288, "status": "空闲"},
            {"id": 2, "name": "豪华双床房", "price": 368, "status": "已入住"},
            {"id": 3, "name": "行政套房", "price": 588, "status": "空闲"},
        ],
        "total": 3,
    }


@router.get("/status", summary="房态总览")
async def room_status():
    return {
        "code": 0,
        "msg": "ok",
        "hotel_id": 1,
        "hotel_name": "伊家酒店",
        "total_rooms": 30,
        "available_total": 12,
        "booked_total": 8,
        "occupied_total": 8,
        "cleaning_total": 2,
        "items": [
            {"id": 1, "name": "标准大床房", "price": 288, "total_count": 10, "available_count": 4, "booked_count": 3, "occupied_count": 2, "cleaning_count": 1},
            {"id": 2, "name": "豪华双床房", "price": 368, "total_count": 12, "available_count": 5, "booked_count": 4, "occupied_count": 3, "cleaning_count": 0},
            {"id": 3, "name": "行政套房", "price": 588, "total_count": 8, "available_count": 3, "booked_count": 1, "occupied_count": 3, "cleaning_count": 1},
        ],
    }


@router.put("/{rid}", summary="修改房型信息")
async def update_room(rid: int, req: dict):
    return {"code": 0, "msg": "修改成功", "data": {"id": rid, **req}}
