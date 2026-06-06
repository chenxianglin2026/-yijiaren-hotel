"""
伊家人酒店系统 - 海康威视摄像头管理 API
方案B: RTSP快照轮询（后端定时截取JPEG快照返回前端）
"""
import base64
import hashlib
import os
import asyncio
import subprocess
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, Camera, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/cameras", tags=["摄像头"])

# ── 简单密码加密（base64 + XOR 混淆） ─────────────
# TODO: P2 安全: 加密密钥应从环境变量 CAMERA_ENCRYPT_KEY 注入，不要硬编码
import sys as _sys
_SECRET_KEY = os.environ.get("CAMERA_ENCRYPT_KEY", "change-me-camera-key").encode()
if _SECRET_KEY == b"change-me-camera-key":
    print("[WARN] CAMERA_ENCRYPT_KEY not set, using default (INSECURE)", file=_sys.stderr)

def _encrypt_password(plain: str) -> str:
    """简单加密：XOR + base64"""
    key = _SECRET_KEY
    data = plain.encode("utf-8")
    encrypted = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    return base64.b64encode(encrypted).decode()

def _decrypt_password(encrypted: str) -> str:
    """解密"""
    key = _SECRET_KEY
    data = base64.b64decode(encrypted)
    decrypted = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    return decrypted.decode("utf-8")


# ── 生成 RTSP URL ──────────────────────────────────
def build_rtsp_url(ip: str, port: int, username: str, password_encrypted: str, channel: int) -> str:
    """构建海康威视 RTSP URL"""
    password = _decrypt_password(password_encrypted)
    # 海康 RTSP 标准格式: rtsp://[username]:[password]@[ip]:[port]/Streaming/Channels/[channel]01
    return f"rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/{channel}01"


# ── Pydantic Schemas ───────────────────────────────
class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="摄像头名称")
    ip: str = Field(..., description="IP地址")
    port: int = Field(554, ge=1, le=65535, description="RTSP端口")
    username: str = Field("admin", max_length=100, description="摄像头用户名")
    password: str = Field(..., description="摄像头密码")
    channel: int = Field(1, ge=1, le=64, description="通道号")
    location: Optional[str] = Field(None, max_length=50, description="位置")
    hotel_id: Optional[int] = Field(None, description="所属门店")


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    ip: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = None  # 可选更新密码
    channel: Optional[int] = Field(None, ge=1, le=64)
    location: Optional[str] = Field(None, max_length=50)
    hotel_id: Optional[int] = None


class CameraOut(BaseModel):
    id: int
    name: str
    ip: str
    port: int
    username: str
    channel: int
    location: Optional[str] = None
    status: str
    rtsp_url: Optional[str] = None
    hotel_id: Optional[int] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ── 管理员权限检查 ──────────────────────────────────
def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作摄像头")
    return user


# ── API 端点 ───────────────────────────────────────

@router.get("", response_model=dict, summary="摄像头列表")
async def list_cameras(
    hotel_id: Optional[int] = Query(None, description="按门店筛选"),
    status: Optional[str] = Query(None, description="按状态筛选 online/offline"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    query = select(Camera)
    if hotel_id is not None:
        query = query.where(Camera.hotel_id == hotel_id)
    if status:
        query = query.where(Camera.status == status)
    query = query.order_by(Camera.id)

    result = await db.execute(query)
    cameras = result.scalars().all()

    items = []
    for c in cameras:
        rtsp = build_rtsp_url(c.ip, c.port, c.username, c.password, c.channel) if c.username and c.password else None
        items.append({
            "id": c.id,
            "name": c.name,
            "ip": c.ip,
            "port": c.port,
            "username": c.username,
            "channel": c.channel,
            "location": c.location,
            "status": c.status,
            "rtsp_url": rtsp,
            "hotel_id": c.hotel_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    return {"code": 0, "data": items, "total": len(items)}


@router.post("", response_model=dict, summary="添加摄像头")
async def create_camera(
    req: CameraCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    encrypted_pw = _encrypt_password(req.password)
    rtsp = build_rtsp_url(req.ip, req.port, req.username, encrypted_pw, req.channel)

    camera = Camera(
        name=req.name,
        ip=req.ip,
        port=req.port,
        username=req.username,
        password=encrypted_pw,
        channel=req.channel,
        location=req.location,
        status="offline",  # 默认离线，等健康检查更新
        rtsp_url=rtsp,
        hotel_id=req.hotel_id,
    )
    db.add(camera)
    await db.flush()
    await db.refresh(camera)

    return {
        "code": 0,
        "data": {
            "id": camera.id,
            "name": camera.name,
            "ip": camera.ip,
            "port": camera.port,
            "username": camera.username,
            "channel": camera.channel,
            "location": camera.location,
            "status": camera.status,
            "rtsp_url": rtsp,
            "hotel_id": camera.hotel_id,
            "created_at": camera.created_at.isoformat() if camera.created_at else None,
            "updated_at": camera.updated_at.isoformat() if camera.updated_at else None,
        },
        "msg": "添加成功",
    }


@router.get("/{camera_id}/stream", response_model=dict, summary="获取RTSP流地址")
async def get_stream_url(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头不存在")

    rtsp = build_rtsp_url(camera.ip, camera.port, camera.username, camera.password, camera.channel)

    return {
        "code": 0,
        "data": {
            "id": camera.id,
            "name": camera.name,
            "rtsp_url": rtsp,
        },
    }


@router.get("/{camera_id}/snapshot", summary="获取摄像头快照（JPEG图片）")
async def get_snapshot(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    方案B: 后端尝试用ffmpeg从RTSP截取一帧JPEG快照返回。
    如果ffmpeg不可用或摄像头离线，返回占位图。
    """
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头不存在")

    rtsp = build_rtsp_url(camera.ip, camera.port, camera.username, camera.password, camera.channel)

    # 尝试用 ffmpeg 抓取快照
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-i", rtsp,
            "-vframes", "1",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-timeout", "5000000",  # 5秒超时（微秒）
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=6.0)

        if proc.returncode == 0 and stdout and len(stdout) > 100:
            # 更新状态为在线
            if camera.status != "online":
                camera.status = "online"
                camera.updated_at = datetime.utcnow()
                await db.flush()

            return StreamingResponse(
                iter([stdout]),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
    except (asyncio.TimeoutError, FileNotFoundError, Exception):
        pass

    # 失败时标记离线
    if camera.status != "offline":
        camera.status = "offline"
        camera.updated_at = datetime.utcnow()
        await db.flush()

    # 返回一个占位的 SVG 图片
    placeholder_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="#1a1a1a"/>
  <rect x="1" y="1" width="638" height="358" fill="none" stroke="#c8a052" stroke-width="2"/>
  <text x="320" y="160" text-anchor="middle" fill="#c8a052" font-size="24" font-family="sans-serif">📷 {camera.name}</text>
  <text x="320" y="195" text-anchor="middle" fill="#888" font-size="16" font-family="sans-serif">状态: 离线 / 无法连接</text>
  <text x="320" y="225" text-anchor="middle" fill="#666" font-size="12" font-family="sans-serif">IP: {camera.ip}:{camera.port} | 通道: CH{camera.channel}</text>
</svg>'''
    return StreamingResponse(
        iter([placeholder_svg.encode()]),
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "no-cache",
        },
    )


@router.put("/{camera_id}", response_model=dict, summary="编辑摄像头")
async def update_camera(
    camera_id: int,
    req: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头不存在")

    if req.name is not None:
        camera.name = req.name
    if req.ip is not None:
        camera.ip = req.ip
    if req.port is not None:
        camera.port = req.port
    if req.username is not None:
        camera.username = req.username
    if req.password is not None:
        camera.password = _encrypt_password(req.password)
    if req.channel is not None:
        camera.channel = req.channel
    if req.location is not None:
        camera.location = req.location
    if req.hotel_id is not None:
        camera.hotel_id = req.hotel_id

    # 更新 RTSP URL
    camera.rtsp_url = build_rtsp_url(camera.ip, camera.port, camera.username, camera.password, camera.channel)
    camera.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(camera)

    rtsp = camera.rtsp_url
    return {
        "code": 0,
        "data": {
            "id": camera.id,
            "name": camera.name,
            "ip": camera.ip,
            "port": camera.port,
            "username": camera.username,
            "channel": camera.channel,
            "location": camera.location,
            "status": camera.status,
            "rtsp_url": rtsp,
            "hotel_id": camera.hotel_id,
            "created_at": camera.created_at.isoformat() if camera.created_at else None,
            "updated_at": camera.updated_at.isoformat() if camera.updated_at else None,
        },
        "msg": "更新成功",
    }


@router.delete("/{camera_id}", response_model=dict, summary="删除摄像头")
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头不存在")

    await db.delete(camera)
    await db.flush()

    return {"code": 0, "msg": f"摄像头 {camera.name} 已删除"}
