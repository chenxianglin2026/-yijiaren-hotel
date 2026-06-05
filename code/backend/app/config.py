"""
伊家人酒店系统 - 配置模块
dev_mode=True 使用 SQLite，否则使用 PostgreSQL
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os


class Settings(BaseSettings):
    # 应用基础
    APP_NAME: str = "伊家人酒店系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 开发模式开关
    DEV_MODE: bool = True

    # 数据库 - dev 模式自动切 SQLite，prod 模式必须配置 DATABASE_URL
    DATABASE_URL: str = ""

    # PostgreSQL 容器连接参数（docker-compose 注入）
    POSTGRES_DB: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url_from_parts(cls, v):
        """如果 DATABASE_URL 为空，尝试从 POSTGRES_* 变量拼接"""
        if v is None or str(v).strip() == "":
            pg_db = os.getenv("POSTGRES_DB", "yijiaren")
            pg_user = os.getenv("POSTGRES_USER", "yijiaren")
            pg_pass = os.getenv("POSTGRES_PASSWORD", "yijiaren123")
            pg_host = os.getenv("POSTGRES_HOST", "postgres")
            pg_port = os.getenv("POSTGRES_PORT", "5432")
            return f"postgresql+asyncpg://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        return v

    @property
    def db_url(self) -> str:
        if self.DEV_MODE:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(db_dir, exist_ok=True)
            return f"sqlite+aiosqlite:///{db_dir}/yijiaren.db"
        if not self.DATABASE_URL:
            raise ValueError(
                "DEV_MODE=False 且未配置 DATABASE_URL，"
                "请设置环境变量 DATABASE_URL 或 POSTGRES_* 系列变量"
            )
        return self.DATABASE_URL

    @property
    def db_sync_url(self) -> str:
        """同步引擎用（seed 脚本等）"""
        if self.DEV_MODE:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(db_dir, exist_ok=True)
            return f"sqlite:///{db_dir}/yijiaren.db"
        return self.DATABASE_URL.replace("+aiosqlite", "")

    # JWT 配置 — CHANGE IN PRODUCTION: set SECRET_KEY env var
    SECRET_KEY: str = "yijiaren-secret-key-change-in-production-2024"  # default only for DEV_MODE
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://43.163.5.90",
    ]

    # 微信小程序配置 — CHANGE IN PRODUCTION: set WX_APPID, WX_SECRET env vars
    WX_APPID: str = "wx15932207fb03a5a4"
    WX_SECRET: str = ""  # must be set via env var or .env in production

    # 服务器域名（用于构建回调URL等）
    SERVER_DOMAIN: str = ""  # e.g. http://43.163.5.90:8001 or https://your-domain.com

    # 微信支付配置
    WX_MCHID: str = ""
    WX_PAY_KEY: str = ""
    WX_PAY_SERIAL: str = ""
    WX_PAY_PRIVATE_KEY: str = ""
    WX_PAY_NOTIFY_URL: str = ""  # 优先使用此项；为空时自动由 SERVER_DOMAIN 拼接

    # 智能门锁配置（TTLock 通通）— CHANGE IN PRODUCTION: set TTLOCK_CLIENT_ID, TTLOCK_CLIENT_SECRET env vars
    TTLOCK_CLIENT_ID: str = ""
    TTLOCK_CLIENT_SECRET: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
