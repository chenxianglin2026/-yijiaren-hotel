"""
伊家人酒店系统 - 认证 API
注册 / 登录 / 微信登录
"""
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.config import settings
from app.db import get_db, User

router = APIRouter(prefix="/api/auth", tags=["认证"])

security = HTTPBearer()


def hash_password(pw: str) -> str:
    """与 seed_mock.py 一致的 SHA-256 密码哈希"""
    salt = os.urandom(16)
    return salt.hex() + "$" + hashlib.sha256(salt + pw.encode()).hexdigest()


def verify_password(pw: str, hashed: str) -> bool:
    """验证密码"""
    try:
        salt_hex, hash_value = hashed.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        return hashlib.sha256(salt + pw.encode()).hexdigest() == hash_value
    except (ValueError, IndexError):
        return False


# ── Schemas ──────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
    nickname: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class WxLoginRequest(BaseModel):
    code: str = Field(..., description="微信小程序登录 code")
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    nickname: Optional[str] = None


class UserInfo(BaseModel):
    id: int
    username: str
    phone: Optional[str]
    role: str
    nickname: Optional[str]
    avatar_url: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


# ── 工具函数 ─────────────────────────────────────────
def _create_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=_create_token(user),
        user_id=user.id,
        username=user.username,
        role=user.role,
        nickname=user.nickname,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT token 解析当前用户（作为依赖注入使用）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


# ── 路由 ─────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已被注册")

    # 检查手机号是否已被使用
    if req.phone:
        phone_exist = await db.execute(select(User).where(User.phone == req.phone))
        if phone_exist.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="手机号已被注册")

    user = User(
        username=req.username,
        phone=req.phone,
        hashed_password=hash_password(req.password),
        nickname=req.nickname or req.username,
        role="guest",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse, summary="用户名密码登录")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    return _token_response(user)


@router.post("/wx-login", response_model=TokenResponse, summary="微信小程序登录")
async def wx_login(req: WxLoginRequest, db: AsyncSession = Depends(get_db)):
    # 开发模式下直接模拟微信登录
    if settings.DEV_MODE or not settings.WX_APPID:
        # 用 code 作为 openid 查找或创建用户
        openid = f"wx_dev_{req.code}"
        result = await db.execute(select(User).where(User.wx_openid == openid))
        user = result.scalar_one_or_none()

        if not user:
            username = f"wx_user_{req.code[:8]}"
            user = User(
                username=username,
                hashed_password=hash_password(openid),
                role="guest",
                nickname=req.nickname or username,
                avatar_url=req.avatar_url,
                wx_openid=openid,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
        else:
            # 更新昵称和头像
            if req.nickname:
                user.nickname = req.nickname
            if req.avatar_url:
                user.avatar_url = req.avatar_url

        return _token_response(user)

    # TODO: 生产环境 — 调用微信 code2session 接口获取 openid
    raise HTTPException(status_code=501, detail="微信登录生产环境暂未对接")


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── 微信手机号一键登录 ──────────────────────────────

import base64
import json as _json
from Crypto.Cipher import AES

class WxPhoneLoginRequest(BaseModel):
    code: str = Field(..., description="wx.login 返回的 code")
    encrypted_data: str = Field(..., description="getPhoneNumber 返回的 encryptedData")
    iv: str = Field(..., description="getPhoneNumber 返回的 iv")
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


async def _wx_code2session(code: str) -> dict:
    """调用微信 code2session 获取 openid + session_key"""
    import httpx
    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={settings.WX_APPID}&secret=***&js_code={code}&grant_type=authorization_code"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        data = resp.json()
        if "errcode" in data and data["errcode"] != 0:
            raise HTTPException(400, f"微信登录失败: {data.get('errmsg', 'unknown')}")
        return data


def _decrypt_phone(encrypted_data: str, iv: str, session_key: str) -> str:
    """AES-128-CBC 解密微信手机号"""
    key = base64.b64decode(session_key)
    iv_bytes = base64.b64decode(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
    raw = cipher.decrypt(base64.b64decode(encrypted_data))
    # PKCS7 unpad
    pad = raw[-1]
    raw = raw[:-pad]
    data = _json.loads(raw.decode("utf-8"))
    return data.get("purePhoneNumber") or data.get("phoneNumber", "")


@router.post("/wechat-phone-login", response_model=TokenResponse, summary="微信手机号一键登录")
async def wechat_phone_login(req: WxPhoneLoginRequest, db: AsyncSession = Depends(get_db)):
    # 开发模式跳过微信 API
    if settings.DEV_MODE:
        phone = "13800138000"
        openid = f"wx_dev_{req.code[:12]}"
    else:
        session_data = await _wx_code2session(req.code)
        openid = session_data["openid"]
        session_key = session_data["session_key"]
        phone = _decrypt_phone(req.encrypted_data, req.iv, session_key)

    # 查用户：先按 openid，再按手机号
    if not settings.DEV_MODE:
        result = await db.execute(select(User).where(User.wx_openid == openid))
    else:
        result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            username=f"wx_{phone[-8:]}",
            phone=phone,
            hashed_password=hash_password(openid if not settings.DEV_MODE else phone),
            role="guest",
            nickname=req.nickname or f"用户{phone[-4:]}",
            avatar_url=req.avatar_url,
            wx_openid=openid,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        if req.nickname:
            user.nickname = req.nickname
        if req.avatar_url:
            user.avatar_url = req.avatar_url
        if not user.wx_openid:
            user.wx_openid = openid
        if not user.phone:
            user.phone = phone

    return _token_response(user)
