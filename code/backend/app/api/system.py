"""
伊家人酒店系统 - 系统管理 API
数据库备份信息、系统状态、系统信息等
"""
import os
import sys
import time as _time_module
from datetime import datetime
from collections import deque

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.config import settings
from app.db import User, get_async_engine
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/system", tags=["系统管理"])

# ── 全局错误日志环形缓冲区（最近50条） ──────────────
_error_log_ring: deque = deque(maxlen=50)


def _get_db_size_info():
    """获取数据库文件大小信息（内部共用）"""
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    db_file = os.path.join(db_dir, "yijiaren.db")

    file_size = 0
    last_modified = None
    exists = os.path.exists(db_file)

    if exists:
        stat = os.stat(db_file)
        file_size = stat.st_size
        last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

    if file_size >= 1024 * 1024:
        size_display = f"{file_size / (1024 * 1024):.2f} MB"
    elif file_size >= 1024:
        size_display = f"{file_size / 1024:.2f} KB"
    else:
        size_display = f"{file_size} B"

    return db_file, file_size, size_display, last_modified, exists


def _detect_container():
    """检测是否运行在 Docker 容器中"""
    # 检查 /.dockerenv 文件
    if os.path.exists("/.dockerenv"):
        return "docker"
    # 检查 cgroup 中是否包含 docker
    cgroup_path = "/proc/1/cgroup"
    if os.path.exists(cgroup_path):
        try:
            with open(cgroup_path, "r") as f:
                content = f.read()
                if "docker" in content or "containerd" in content:
                    return "docker"
        except Exception:
            pass
    # 检查 KUBERNETES_SERVICE_HOST (k8s)
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return "kubernetes"
    return "bare-metal"


@router.get("/info", summary="获取系统信息")
async def get_system_info(request: Request):
    """返回系统版本、运行时间、数据库大小、容器状态（无需认证）"""
    start_time = getattr(request.app.state, "start_time", None)
    uptime_seconds = int(_time_module.time() - start_time) if start_time else 0

    # 格式化运行时间
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    uptime_display = " ".join(parts)

    db_file, file_size, size_display, last_modified, db_exists = _get_db_size_info()
    container = _detect_container()

    # 查询门店数和房间数
    hotel_count = 0
    room_count = 0
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            r = await conn.execute(text("SELECT COUNT(*) FROM hotels WHERE is_active=1"))
            hotel_count = r.scalar() or 0
            r = await conn.execute(text("SELECT COUNT(*) FROM rooms WHERE is_active=1"))
            room_count = r.scalar() or 0
    except Exception:
        pass

    return {
        "code": 0,
        "data": {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "dev_mode": settings.DEV_MODE,
            "uptime_seconds": uptime_seconds,
            "uptime_display": uptime_display,
            "db_size": file_size,
            "db_size_display": size_display,
            "db_last_modified": last_modified,
            "db_exists": db_exists,
            "db_type": "SQLite" if settings.DEV_MODE else "PostgreSQL",
            "container": container,
            "python_version": sys.version,
            "hotel_count": hotel_count,
            "room_count": room_count,
        },
    }


# ── 错误日志公共函数 ──────────────────────────────

def log_error(endpoint: str, message: str, status_code: int = 500):
    """记录错误到环形缓冲区（供中间件或其他模块调用）"""
    _error_log_ring.append({
        "ts": datetime.now().isoformat(),
        "endpoint": endpoint,
        "message": str(message)[:500],
        "status": status_code,
    })


@router.get("/errors", summary="获取最近错误日志")
async def get_error_logs(current_user: User = Depends(get_current_user)):
    """返回最近50条错误日志（环形缓冲区）"""
    logs = list(_error_log_ring)
    # 返回最近10条，按时间倒序
    recent = logs[-10:] if len(logs) > 10 else logs
    recent.reverse()
    return {"code": 0, "data": recent, "total": len(logs)}


@router.get("/db-pool", summary="获取数据库连接池状态")
async def get_db_pool_status(current_user: User = Depends(get_current_user)):
    """返回数据库连接池状态信息"""
    engine = get_async_engine()
    pool = engine.pool
    # SQLAlchemy 不同 pool 类型有不同接口，安全获取
    pool_info: dict = {
        "db_type": "SQLite" if settings.DEV_MODE else "PostgreSQL",
    }
    try:
        pool_info["pool_size"] = getattr(pool, "size", lambda: -1)()
    except Exception:
        pool_info["pool_size"] = None
    try:
        pool_info["checked_in"] = getattr(pool, "checkedin", lambda: -1)()
    except Exception:
        pool_info["checked_in"] = None
    try:
        pool_info["overflow"] = getattr(pool, "overflow", lambda: -1)()
    except Exception:
        pool_info["overflow"] = None
    try:
        pool_info["total"] = getattr(pool, "total", lambda: -1)()
    except Exception:
        pool_info["total"] = None
    pool_info["pool_type"] = type(pool).__name__

    return {"code": 0, "data": pool_info}


@router.get("/backup-info", summary="获取数据库备份信息")
async def get_backup_info(current_user: User = Depends(get_current_user)):
    """返回数据库文件大小和最后修改时间"""
    db_file, file_size, size_display, last_modified, exists = _get_db_size_info()

    return {
        "code": 0,
        "data": {
            "db_file": db_file if exists else None,
            "file_size": file_size,
            "file_size_display": size_display,
            "last_modified": last_modified,
            "last_backup": None,  # TODO: 自动备份功能待开发
            "exists": exists,
            "db_type": "SQLite" if settings.DEV_MODE else "PostgreSQL",
        },
    }


# ── Settings JSON 文件持久化 ──────────────────────────
import json as _json

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "system_settings.json")

DEFAULT_SETTINGS = {
    "notification": {
        "order_notify": True,
        "checkin_notify": True,
        "alert_notify": False,
    }
}


def _load_settings() -> dict:
    """从 JSON 文件加载系统设置"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = _json.load(f)
            # 合并默认值，确保新字段有默认值
            merged = DEFAULT_SETTINGS.copy()
            _deep_merge(merged, saved)
            return merged
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()


def _save_settings(data: dict):
    """保存系统设置到 JSON 文件"""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        _json.dump(data, f, ensure_ascii=False, indent=2)


def _deep_merge(base: dict, override: dict):
    """深度合并 override 到 base"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


@router.get("/settings", summary="获取系统设置")
async def get_settings(current_user: User = Depends(get_current_user)):
    """返回通知配置等系统设置（需认证）"""
    return {"code": 0, "data": _load_settings()}


@router.post("/settings", summary="保存系统设置")
async def save_settings(payload: dict, current_user: User = Depends(get_current_user)):
    """保存通知配置等系统设置（需认证）

    请求体示例:
    {
        "notification": {
            "order_notify": true,
            "checkin_notify": true,
            "alert_notify": false
        }
    }
    """
    current = _load_settings()
    _deep_merge(current, payload)
    _save_settings(current)
    return {"code": 0, "msg": "保存成功", "data": current}
