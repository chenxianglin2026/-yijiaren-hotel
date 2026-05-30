"""
伊家人酒店系统 - FastAPI 入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.api import auth, hotels, orders, checkin, rooms, cleaning, dashboard, finance, devices


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化数据库表
    await init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    print(f"   DEV_MODE={settings.DEV_MODE}")
    print(f"   数据库: {settings.db_url}")
    yield
    # 关闭时清理（如有需要）


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="伊家人酒店管理系统后台 API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(hotels.router)
app.include_router(orders.router)
app.include_router(checkin.router)
app.include_router(rooms.router)
app.include_router(cleaning.router)
app.include_router(dashboard.router)
app.include_router(finance.router)
app.include_router(devices.router)


# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

@app.get("/")
async def root():
    return {"app": "伊家人酒店系统", "api": "/api/hotels", "docs": "/docs"}


# Swagger 文档在 /docs
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
