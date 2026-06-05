"""
伊家人酒店系统 - 系统管理 API
数据库备份信息、系统状态等
"""
import os
from datetime import datetime

from fastapi import APIRouter, Depends

from app.config import settings
from app.db import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/system", tags=["系统管理"])


@router.get("/backup-info", summary="获取数据库备份信息")
async def get_backup_info(current_user: User = Depends(get_current_user)):
    """返回数据库文件大小和最后修改时间"""
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    db_file = os.path.join(db_dir, "yijiaren.db")

    file_size = 0
    last_modified = None
    exists = os.path.exists(db_file)

    if exists:
        stat = os.stat(db_file)
        file_size = stat.st_size
        last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

    # 格式化文件大小
    if file_size >= 1024 * 1024:
        size_display = f"{file_size / (1024 * 1024):.2f} MB"
    elif file_size >= 1024:
        size_display = f"{file_size / 1024:.2f} KB"
    else:
        size_display = f"{file_size} B"

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
