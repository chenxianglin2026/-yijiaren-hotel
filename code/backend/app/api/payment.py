"""
微信支付 V3 API 模块
- JSAPI 下单（小程序支付）
- 支付回调通知
- 订单查询 / 退款

配置占位符，待商户号就位后填入真实值。
"""

import hashlib, time, json, uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, User, Order, OrderStatus
from app.api.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/payment", tags=["微信支付"])


# ── 微信支付配置 ──────────────────────────────────
class WxPayConfig:
    APPID = settings.WX_APPID or "wx15932207fb03a5a4"         # {{PAY_APPID}}
    MCHID = settings.WX_MCHID or "{{PAY_MCHID}}"              # {{PAY_MCHID}}
    API_V3_KEY = settings.WX_PAY_KEY or "{{PAY_API_V3_KEY}}"  # {{PAY_API_V3_KEY}}
    NOTIFY_URL = settings.WX_PAY_NOTIFY_URL or "http://43.163.5.90:8001/api/payment/notify"
    SERIAL_NO = settings.WX_PAY_SERIAL or "{{PAY_SERIAL_NO}}" # {{PAY_SERIAL_NO}}
    PRIVATE_KEY = settings.WX_PAY_PRIVATE_KEY or ""           # {{PAY_PRIVATE_KEY}}


# ── Schemas ───────────────────────────────────────
class PayRequest(BaseModel):
    order_id: int
    openid: Optional[str] = None  # 小程序用户 openid（JSAPI 必填）


class PayResponse(BaseModel):
    code: int = 0
    data: Optional[dict] = None
    msg: str = "ok"


# ── 工具函数 ──────────────────────────────────────
def _generate_order_no() -> str:
    return f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


def _sign(method: str, url: str, body: str = "") -> str:
    """微信支付 V3 签名"""
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex[:32]
    message = f"{method}\n{url}\n{ts}\n{nonce}\n{body}\n"
    # TODO: 真实 RSA-SHA256 签名需证书
    # import base64
    # from cryptography.hazmat.primitives import hashes, serialization
    # from cryptography.hazmat.primitives.asymmetric import padding
    # key = serialization.load_pem_private_key(WxPayConfig.PRIVATE_KEY.encode(), None)
    # sig = key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
    # return base64.b64encode(sig).decode()
    return f"mchid={WxPayConfig.MCHID},nonce_str={nonce},signature=PLACEHOLDER,timestamp={ts},serial_no={WxPayConfig.SERIAL_NO}"


# ── 路由 ─────────────────────────────────────────
@router.post("/create", response_model=PayResponse, summary="创建支付（JSAPI下单）")
async def create_payment(
    req: PayRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """生成微信支付参数，小程序端调起支付"""
    # 查询订单
    result = await db.execute(select(Order).where(Order.id == req.order_id, Order.user_id == user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "订单不存在")
    if order.status not in (OrderStatus.PENDING,):
        raise HTTPException(400, f"订单状态不可支付: {order.status}")

    # 生成微信支付单号
    out_trade_no = _generate_order_no()

    # 构建 JSAPI 下单请求体
    pay_body = {
        "appid": WxPayConfig.APPID,
        "mchid": WxPayConfig.MCHID,
        "description": f"伊家人酒店-{order.order_no}",
        "out_trade_no": out_trade_no,
        "notify_url": WxPayConfig.NOTIFY_URL,
        "amount": {
            "total": int(order.total_price * 100),  # 分
            "currency": "CNY",
        },
        "payer": {"openid": req.openid or "{{USER_OPENID}}"},
    }

    # TODO: 真实环境调用 https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi
    # 当前返回模拟数据供前端调试
    mock_prepay_id = f"prepay_{out_trade_no}"
    
    # 小程序调起支付所需参数
    pay_params = {
        "appId": WxPayConfig.APPID,
        "timeStamp": str(int(time.time())),
        "nonceStr": uuid.uuid4().hex[:32],
        "package": f"prepay_id={mock_prepay_id}",
        "signType": "RSA",
        "paySign": "MOCK_SIGN_FOR_DEV",
        "outTradeNo": out_trade_no,
    }

    # 订单状态保持 pending，等待支付回调通知更新
    # 注：真实微信支付成功后通过 /notify 回调更新为 paid
    await db.flush()

    return PayResponse(data={"prepay_id": mock_prepay_id, "pay_params": pay_params, "out_trade_no": out_trade_no})


@router.post("/notify", response_model=dict, summary="支付结果通知（微信回调）")
async def payment_notify(request: Request, db: AsyncSession = Depends(get_db)):
    """接收微信支付异步通知"""
    body = await request.body()
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(400, "无效的请求数据格式")

    # TODO: 验签
    event_type = data.get("event_type", "")
    resource = data.get("resource", {})
    
    if event_type == "TRANSACTION.SUCCESS":
        # 解密 resource 获取订单信息
        out_trade_no = resource.get("out_trade_no", "")
        
        # 查找对应订单并更新状态
        # result = await db.execute(select(Order).where(Order.out_trade_no == out_trade_no))
        # order = result.scalar_one_or_none()
        # if order:
        #     order.status = OrderStatus.PAID
        #     order.paid_at = datetime.utcnow()
        #     await db.commit()
        
        return {"code": "SUCCESS", "message": "OK"}
    
    return {"code": "SUCCESS", "message": ""}


@router.get("/query/{order_id}", response_model=PayResponse, summary="查询支付状态")
async def query_payment(order_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "订单不存在")
    return PayResponse(data={"order_no": order.order_no, "status": order.status, "total_price": order.total_price, "paid_at": order.paid_at.isoformat() if order.paid_at else None})


@router.post("/refund", response_model=PayResponse, summary="申请退款")
async def refund_order(
    order_id: int,
    reason: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "订单不存在")
    if order.status not in (OrderStatus.PAID, OrderStatus.CHECKED_IN):
        raise HTTPException(400, "当前状态不可退款")

    # TODO: 调用微信退款 API
    order.status = OrderStatus.CANCELLED
    order.cancel_reason = reason or "用户申请退款"
    order.cancelled_at = datetime.utcnow()
    await db.flush()

    return PayResponse(msg="退款申请已提交")
