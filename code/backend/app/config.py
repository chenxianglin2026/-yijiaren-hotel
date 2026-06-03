"""
伊家人酒店系统 - 配置模块
dev_mode=True 使用 SQLite，否则使用 PostgreSQL
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # 应用基础
    APP_NAME: str = "伊家人酒店系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 开发模式开关
    DEV_MODE: bool = True

    # 数据库 - dev 模式自动切 SQLite
    DATABASE_URL: str = ""

    @property
    def db_url(self) -> str:
        if self.DEV_MODE:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(db_dir, exist_ok=True)
            return f"sqlite+aiosqlite:///{db_dir}/yijiaren.db"
        return self.DATABASE_URL

    @property
    def db_sync_url(self) -> str:
        """同步引擎用（seed 脚本等）"""
        if self.DEV_MODE:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(db_dir, exist_ok=True)
            return f"sqlite:///{db_dir}/yijiaren.db"
        return self.DATABASE_URL.replace("+aiosqlite", "")

    # JWT 配置
    SECRET_KEY: str = "yijiaren-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # 微信小程序配置
    WX_APPID: str = "wx15932207fb03a5a4"
    WX_SECRET: str = "97acd5a0ca02fd5b03814fc51a34e9fa"

    # 微信支付配置
    WX_MCHID: str = ""
    WX_PAY_KEY: str = ""
    WX_PAY_SERIAL: str = ""
    WX_PAY_PRIVATE_KEY: str = ""
    WX_PAY_NOTIFY_URL: str = ""

    # 智能门锁配置（TTLock 通通）
    TTLOCK_CLIENT_ID: str = "4433c6c075e8490ea00c6a60a9e31cd8"
    TTLOCK_CLIENT_SECRET: str = "8b**...*ac1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
