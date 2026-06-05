"""
伊家人酒店系统 - FastAPI 入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.api import auth, hotels, orders, checkin, rooms, cleaning, dashboard, finance, devices, payment, lock, ota, system


import time as _time_module

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化数据库表
    await init_db()
    app.state.start_time = _time_module.time()
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
app.include_router(payment.router)
app.include_router(lock.router)
app.include_router(ota.router)
app.include_router(system.router)

# 托管管理后台静态文件（本地调试用，生产由nginx处理）
import os
admin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'admin')
if os.path.exists(admin_path):
    app.mount("/admin", StaticFiles(directory=admin_path, html=True), name="admin")


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
