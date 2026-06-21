"""
伊家人酒店系统 — 内容管理 API
酒店介绍/房型实景/周边推荐/精选评价 — JSON文件存储
"""
from fastapi import APIRouter, Depends, HTTPException
from app.api.auth import get_current_user
from app.db import User
from pydantic import BaseModel
from typing import Optional
import json
import os

router = APIRouter(prefix="/api/content", tags=["内容管理"])

CONTENT_FILE = "/home/ubuntu/projects/yijiaren/data/content.json"
# 本地开发 fallback
if not os.path.exists(CONTENT_FILE):
    _local = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "content.json")
    if os.path.exists(_local):
        CONTENT_FILE = _local

def _load():
    try:
        with open(CONTENT_FILE) as f:
            return json.load(f)
    except:
        return {"hotels": [], "galleries": [], "surroundings": [], "reviews_show": []}

def _save(d):
    os.makedirs(os.path.dirname(CONTENT_FILE), exist_ok=True)
    with open(CONTENT_FILE, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ======== 酒店介绍 ========
class HotelIntro(BaseModel):
    hotel_id: int
    name: str
    desc: str = ""
    cover: str = ""
    features: list[str] = []
    facilities: list[str] = []      # 酒店设施
    checkin_time: str = "14:00"
    checkout_time: str = "12:00"

@router.get("/hotels")
async def list_hotel_intros(hotel_id: int = 0):
    d = _load(); h = d["hotels"]
    if hotel_id: h = [x for x in h if x.get("hotel_id") == hotel_id]
    return h

@router.post("/hotels")
async def save_hotel_intro(req: HotelIntro, user: User = Depends(get_current_user)):
    d = _load()
    for i, x in enumerate(d["hotels"]):
        if x.get("hotel_id") == req.hotel_id:
            d["hotels"][i] = req.model_dump()
            _save(d)
            return {"ok": True, "id": req.hotel_id}
    d["hotels"].append(req.model_dump())
    _save(d)
    return {"ok": True, "id": req.hotel_id}

@router.delete("/hotels")
async def del_hotel_intro(hotel_id: int, user: User = Depends(get_current_user)):
    d = _load()
    d["hotels"] = [x for x in d["hotels"] if x.get("hotel_id") != hotel_id]
    _save(d)
    return {"ok": True}

# ======== 房型实景 ========
class RoomGallery(BaseModel):
    room_id: int
    room_name: str
    room_type: str = ""
    images: list[str] = []
    video: str = ""
    vr_url: str = ""
    desc: str = ""
    amenities: list[str] = []       # 设备设施
    perks: list[str] = []           # 赠品权益

@router.get("/gallery")
async def list_galleries(room_id: int = 0):
    d = _load(); g = d["galleries"]
    if room_id: g = [x for x in g if x.get("room_id") == room_id]
    return g

@router.post("/gallery")
async def save_gallery(req: RoomGallery, user: User = Depends(get_current_user)):
    d = _load()
    for i, x in enumerate(d["galleries"]):
        if x.get("room_id") == req.room_id:
            d["galleries"][i] = req.model_dump()
            _save(d)
            return {"ok": True}
    d["galleries"].append(req.model_dump())
    _save(d)
    return {"ok": True}

@router.delete("/gallery")
async def del_gallery(room_id: int, user: User = Depends(get_current_user)):
    d = _load()
    d["galleries"] = [x for x in d["galleries"] if x.get("room_id") != room_id]
    _save(d)
    return {"ok": True}

# ======== 周边推荐 ========
class Surrounding(BaseModel):
    name: str
    type: str = "餐饮"
    address: str = ""
    distance: str = ""
    rating: float = 4.5
    image: str = ""
    desc: str = ""
    lat: float = 0
    lng: float = 0
    phone: str = ""

@router.get("/surrounding")
async def list_surroundings(type: str = ""):
    d = _load(); s = d["surroundings"]
    if type: s = [x for x in s if x.get("type") == type]
    return s

@router.post("/surrounding")
async def upsert_surrounding(req: Surrounding, user: User = Depends(get_current_user)):
    d = _load()
    found = False
    for i, x in enumerate(d["surroundings"]):
        if x.get("name") == req.name:
            d["surroundings"][i] = req.model_dump()
            found = True; break
    if not found: d["surroundings"].append(req.model_dump())
    _save(d)
    return {"ok": True}

@router.delete("/surrounding")
async def del_surrounding(name: str, user: User = Depends(get_current_user)):
    d = _load()
    d["surroundings"] = [x for x in d["surroundings"] if x.get("name") != name]
    _save(d)
    return {"ok": True}

# ======== 评价展示管理 ========
class ReviewShow(BaseModel):
    user_name: str
    rating: int
    content: str
    images: list[str] = []
    date: str = ""

@router.get("/reviews-show")
async def list_reviews_show():
    d = _load()
    return d.get("reviews_show", [])

@router.post("/reviews-show")
async def add_review_show(req: ReviewShow, user: User = Depends(get_current_user)):
    d = _load()
    d.setdefault("reviews_show", []).append(req.model_dump())
    _save(d)
    return {"ok": True}

@router.delete("/reviews-show")
async def del_review_show(index: int, user: User = Depends(get_current_user)):
    d = _load()
    rs = d.get("reviews_show", [])
    if 0 <= index < len(rs): rs.pop(index)
    d["reviews_show"] = rs
    _save(d)
    return {"ok": True}
