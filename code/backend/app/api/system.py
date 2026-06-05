"""
伊家人酒店系统 - 系统管理 API
数据库备份信息、系统状态、系统信息等
"""
import os
import time as _time_module
from datetime import datetime

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.db import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/system", tags=["系统管理"])


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
        },
    }


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
