"""
伊家人酒店系统 - 保洁工单 API
创建工单 / 接单 / 完工打卡拍照 / 工单列表
同时包含在店服务（呼叫保洁/送物/维修报修）
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, get_db, User, Hotel
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/cleaning", tags=["保洁管理"])


# ══════════════════════════════════════════════════════
# 数据模型（动态扩展，不影响原有 db.py）
# ══════════════════════════════════════════════════════

class CleaningTask(Base):
    """保洁工单"""
    __tablename__ = "cleaning_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), index=True)
    room_number: Mapped[str] = mapped_column(String(20), comment="房间号")
    task_type: Mapped[str] = mapped_column(String(30), default="cleanup", comment="cleanup/daily/turndown/deep_clean")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True,
                                         comment="pending/accepted/in_progress/completed/cancelled")
    cleaner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    creator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    photo_urls: Mapped[Optional[str]] = mapped_column(Text, comment="完工照片 JSON 数组")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 关系
    hotel: Mapped["Hotel"] = relationship(back_populates=None)


class ServiceRequest(Base):
    """在店服务请求（呼叫保洁/送物/维修报修）"""
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), index=True)
    room_number: Mapped[str] = mapped_column(String(20), comment="房间号")
    request_type: Mapped[str] = mapped_column(String(20), comment="cleaning/delivery/maintenance/other")
    description: Mapped[str] = mapped_column(Text, default="", comment="详细描述")
    priority: Mapped[str] = mapped_column(String(10), default="normal", comment="normal/urgent")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True,
                                         comment="pending/accepted/processing/completed/cancelled")
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    photo_urls: Mapped[Optional[str]] = mapped_column(Text, comment="照片 JSON")
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="处理备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


# ══════════════════════════════════════════════════════
# Pydantic Schemas
# ══════════════════════════════════════════════════════

class CleaningTaskCreate(BaseModel):
    hotel_id: int
    room_number: str
    task_type: str = "cleanup"
    notes: Optional[str] = None


class CleaningTaskOut(BaseModel):
    id: int
    hotel_id: int
    room_number: str
    task_type: str
    status: str
    cleaner_id: Optional[int] = None
    notes: Optional[str] = None
    photo_urls: Optional[str] = None
    created_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CleaningAccept(BaseModel):
    """接单（保洁员使用）"""
    task_id: int


class CleaningComplete(BaseModel):
    """完工打卡（保洁员使用）"""
    task_id: int
    photo_urls: Optional[str] = None  # JSON 数组字符串
    notes: Optional[str] = None


class ServiceRequestCreate(BaseModel):
    hotel_id: int
    room_number: str
    request_type: str  # cleaning / delivery / maintenance / other
    description: str = ""
    priority: str = "normal"


class ServiceRequestOut(BaseModel):
    id: int
    user_id: int
    hotel_id: int
    room_number: str
    request_type: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[int] = None
    photo_urls: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    total: int
    items: list[CleaningTaskOut]


class ServiceListResponse(BaseModel):
    total: int
    items: list[ServiceRequestOut]


# ══════════════════════════════════════════════════════
# 保洁工单 API
# ══════════════════════════════════════════════════════

@router.post("/tasks", response_model=CleaningTaskOut, summary="创建保洁工单")
async def create_cleaning_task(
    req: CleaningTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员/前台创建保洁工单"""
    if current_user.role not in ("admin", "front_desk", "cleaner"):
        raise HTTPException(status_code=403, detail="无权限创建保洁工单")

    task = CleaningTask(
        hotel_id=req.hotel_id,
        room_number=req.room_number,
        task_type=req.task_type,
        status="pending",
        creator_id=current_user.id,
        notes=req.notes,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return CleaningTaskOut.model_validate(task)


@router.get("/tasks", response_model=TaskListResponse, summary="保洁工单列表")
async def list_cleaning_tasks(
    hotel_id: Optional[int] = Query(None, description="门店ID"),
    status: Optional[str] = Query(None, description="状态筛选 pending/accepted/in_progress/completed"),
    cleaner_id: Optional[int] = Query(None, description="保洁员ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询保洁工单列表 - 保洁员只看自己的"""
    query = select(CleaningTask)

    # 保洁员只能看自己的工单
    if current_user.role == "cleaner":
        query = query.where(CleaningTask.cleaner_id == current_user.id)

    if hotel_id:
        query = query.where(CleaningTask.hotel_id == hotel_id)
    if status:
        query = query.where(CleaningTask.status == status)
    if cleaner_id and current_user.role != "cleaner":
        query = query.where(CleaningTask.cleaner_id == cleaner_id)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(CleaningTask.created_at.desc()).offset(offset).limit(page_size)
    )
    tasks = result.scalars().all()

    return TaskListResponse(
        total=total,
        items=[CleaningTaskOut.model_validate(t) for t in tasks],
    )


@router.get("/tasks/{task_id}", response_model=CleaningTaskOut, summary="工单详情")
async def get_cleaning_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(CleaningTask).where(CleaningTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="工单不存在")
    if current_user.role == "cleaner" and task.cleaner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看他人工单")
    return CleaningTaskOut.model_validate(task)


@router.post("/tasks/accept", response_model=CleaningTaskOut, summary="保洁员接单")
async def accept_cleaning_task(
    req: CleaningAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保洁员接单"""
    if current_user.role not in ("cleaner", "admin"):
        raise HTTPException(status_code=403, detail="仅保洁员可接单")

    result = await db.execute(
        select(CleaningTask).where(CleaningTask.id == req.task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="工单不存在")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="工单已被接取或已完成")

    task.cleaner_id = current_user.id
    task.status = "accepted"
    task.accepted_at = datetime.utcnow()

    await db.flush()
    await db.refresh(task)
    return CleaningTaskOut.model_validate(task)


@router.post("/tasks/start", response_model=CleaningTaskOut, summary="开始清洁")
async def start_cleaning(
    req: CleaningAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保洁员开始清洁（accepted -> in_progress）"""
    result = await db.execute(
        select(CleaningTask).where(CleaningTask.id == req.task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="工单不存在")
    if task.cleaner_id != current_user.id:
        raise HTTPException(status_code=403, detail="该工单不属于您")
    if task.status != "accepted":
        raise HTTPException(status_code=400, detail="工单状态不允许开始清洁")

    task.status = "in_progress"
    await db.flush()
    await db.refresh(task)
    return CleaningTaskOut.model_validate(task)


@router.post("/tasks/complete", response_model=CleaningTaskOut, summary="完工打卡拍照")
async def complete_cleaning(
    req: CleaningComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保洁员完工打卡，上传完工照片"""
    result = await db.execute(
        select(CleaningTask).where(CleaningTask.id == req.task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="工单不存在")
    if task.cleaner_id != current_user.id:
        raise HTTPException(status_code=403, detail="该工单不属于您")
    if task.status not in ("accepted", "in_progress"):
        raise HTTPException(status_code=400, detail="工单状态不允许完工")

    task.status = "completed"
    task.completed_at = datetime.utcnow()
    if req.photo_urls:
        task.photo_urls = req.photo_urls
    if req.notes:
        task.notes = (task.notes or "") + "\n" + req.notes

    await db.flush()
    await db.refresh(task)
    return CleaningTaskOut.model_validate(task)


@router.get("/my-tasks", response_model=TaskListResponse, summary="我的保洁工单")
async def my_cleaning_tasks(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保洁员查看自己的工单"""
    query = select(CleaningTask).where(CleaningTask.cleaner_id == current_user.id)
    if status:
        query = query.where(CleaningTask.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(CleaningTask.created_at.desc()).offset(offset).limit(page_size)
    )
    tasks = result.scalars().all()

    return TaskListResponse(
        total=total,
        items=[CleaningTaskOut.model_validate(t) for t in tasks],
    )


# ══════════════════════════════════════════════════════
# 在店服务 API（呼叫保洁/送物/维修报修）
# ══════════════════════════════════════════════════════

@router.post("/service", response_model=ServiceRequestOut, summary="发起在店服务请求")
async def create_service_request(
    req: ServiceRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """住客发起服务请求：呼叫保洁/送物/维修报修"""
    sr = ServiceRequest(
        user_id=current_user.id,
        hotel_id=req.hotel_id,
        room_number=req.room_number,
        request_type=req.request_type,
        description=req.description,
        priority=req.priority,
        status="pending",
    )
    db.add(sr)
    await db.flush()
    await db.refresh(sr)
    return ServiceRequestOut.model_validate(sr)


@router.get("/service", response_model=ServiceListResponse, summary="服务请求列表")
async def list_service_requests(
    hotel_id: Optional[int] = Query(None),
    request_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询服务请求列表"""
    query = select(ServiceRequest)

    # 住客只看自己的
    if current_user.role == "guest":
        query = query.where(ServiceRequest.user_id == current_user.id)

    if hotel_id:
        query = query.where(ServiceRequest.hotel_id == hotel_id)
    if request_type:
        query = query.where(ServiceRequest.request_type == request_type)
    if status:
        query = query.where(ServiceRequest.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(ServiceRequest.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return ServiceListResponse(
        total=total,
        items=[ServiceRequestOut.model_validate(s) for s in items],
    )


@router.get("/service/{request_id}", response_model=ServiceRequestOut, summary="服务请求详情")
async def get_service_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))
    sr = result.scalar_one_or_none()
    if not sr:
        raise HTTPException(status_code=404, detail="服务请求不存在")
    if current_user.role == "guest" and sr.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看他人的服务请求")
    return ServiceRequestOut.model_validate(sr)


@router.post("/service/{request_id}/accept", response_model=ServiceRequestOut, summary="接取服务请求")
async def accept_service_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """前台/保洁员接取服务请求"""
    if current_user.role not in ("admin", "front_desk", "cleaner"):
        raise HTTPException(status_code=403, detail="无权限")

    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))
    sr = result.scalar_one_or_none()
    if not sr:
        raise HTTPException(status_code=404, detail="服务请求不存在")
    if sr.status != "pending":
        raise HTTPException(status_code=400, detail="服务请求已被接取或已完成")

    sr.status = "accepted"
    sr.assigned_to = current_user.id
    sr.accepted_at = datetime.utcnow()
    await db.flush()
    await db.refresh(sr)
    return ServiceRequestOut.model_validate(sr)


@router.post("/service/{request_id}/complete", response_model=ServiceRequestOut, summary="完成服务请求")
async def complete_service_request(
    request_id: int,
    remark: Optional[str] = None,
    photo_urls: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """完成服务请求"""
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))
    sr = result.scalar_one_or_none()
    if not sr:
        raise HTTPException(status_code=404, detail="服务请求不存在")
    if sr.status not in ("accepted", "processing"):
        raise HTTPException(status_code=400, detail="服务请求状态不允许完成操作")

    sr.status = "completed"
    sr.completed_at = datetime.utcnow()
    if remark:
        sr.remark = remark
    if photo_urls:
        sr.photo_urls = photo_urls
    await db.flush()
    await db.refresh(sr)
    return ServiceRequestOut.model_validate(sr)


@router.get("/service-stats", summary="服务请求统计")
async def service_stats(
    hotel_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取各类型待处理数量统计"""
    query = select(ServiceRequest).where(ServiceRequest.status == "pending")
    if hotel_id:
        query = query.where(ServiceRequest.hotel_id == hotel_id)

    result = await db.execute(query)
    items = result.scalars().all()

    stats = {"total": len(items), "cleaning": 0, "delivery": 0, "maintenance": 0, "other": 0}
    for item in items:
        stats[item.request_type] = stats.get(item.request_type, 0) + 1

    return stats


# ══════════════════════════════════════════════════════
# 保洁员信息
# ══════════════════════════════════════════════════════

class CleanerInfo(BaseModel):
    id: int
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    completed_today: int = 0

    model_config = {"from_attributes": True}


@router.get("/cleaners", summary="保洁员列表")
async def list_cleaners(
    hotel_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取保洁员列表及其工单统计"""
    query = select(User).where(User.role == "cleaner", User.is_active == True)
    result = await db.execute(query)
    cleaners = result.scalars().all()

    cleaner_list = []
    for c in cleaners:
        # 统计待接单
        pending_q = select(func.count()).select_from(
            select(CleaningTask).where(
                CleaningTask.cleaner_id == c.id, CleaningTask.status == "pending"
            ).subquery()
        )
        pending_count = (await db.execute(pending_q)).scalar() or 0

        # 统计进行中
        in_progress_q = select(func.count()).select_from(
            select(CleaningTask).where(
                CleaningTask.cleaner_id == c.id,
                CleaningTask.status.in_(["accepted", "in_progress"]),
            ).subquery()
        )
        in_progress_count = (await db.execute(in_progress_q)).scalar() or 0

        # 今日已完成
        today = datetime.utcnow().date()
        completed_q = select(func.count()).select_from(
            select(CleaningTask).where(
                CleaningTask.cleaner_id == c.id,
                CleaningTask.status == "completed",
                CleaningTask.completed_at >= today,
            ).subquery()
        )
        completed_today = (await db.execute(completed_q)).scalar() or 0

        cleaner_list.append({
            "id": c.id,
            "nickname": c.nickname,
            "avatar_url": c.avatar_url,
            "phone": c.phone,
            "pending_tasks": pending_count,
            "in_progress_tasks": in_progress_count,
            "completed_today": completed_today,
        })

    return cleaner_list
