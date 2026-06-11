# 伊家人酒店系统 API 文档

> 版本: 1.0.0 | 基础地址: `http://localhost:8001` | 认证: Bearer JWT Token

---

## 通用说明

### 响应格式

本项目存在两类响应格式:

**格式 A - 统一包裹** `{code, data, msg}`:
- code=0 表示成功，非0表示错误
- 用于 CRUD 操作、设备、摄像头、仪表盘、财务、系统、支付、OTA、门锁等

**格式 B - 裸对象** (直接返回数据模型):
- 用于查询类端点: 门店详情/房型列表、订单、入住、保洁、认证
- FastAPI 自动序列化 Pydantic 模型

**特殊**:
- `/api/auth/users` 返回 `{code, data, total}` (格式A变体)
- `/api/cleaning/service-stats` 返回裸 `dict`
- `/api/cleaning/cleaners` 返回裸 `list`
- `/api/dashboard/perf` 返回 `{code, data, msg}` (格式A)

### 认证

所有需要认证的端点需在 Header 中携带:
```
Authorization: Bearer <access_token>
```

### 错误响应

- 400: 参数错误
- 401: 未认证或 token 无效
- 403: 权限不足
- 404: 资源不存在
- 500: 服务器内部错误 (`{code: 1, msg: "..."}`)

---

## 1. 认证模块 `/api/auth`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| POST | `/api/auth/register` | 否 | 裸 TokenResponse | 用户注册 |
| POST | `/api/auth/login` | 否 | 裸 TokenResponse | 用户名密码登录 |
| POST | `/api/auth/wx-login` | 否 | 裸 TokenResponse | 微信小程序登录(DEV_MODE模拟) |
| POST | `/api/auth/wechat-phone-login` | 否 | 裸 TokenResponse | 微信手机号一键登录 |
| GET | `/api/auth/me` | 是 | 裸 UserInfo | 获取当前用户信息 |
| GET | `/api/auth/users` | 是(admin) | `{code, data, total}` | 用户列表 |

### 请求/响应示例

**POST /api/auth/login**
```json
// 请求
{"username": "admin", "password": "admin123"}
// 响应
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "admin",
  "role": "admin",
  "nickname": "管理员"
}
```

**POST /api/auth/register**
```json
// 请求
{"username": "zhangsan", "password": "pass123456", "phone": "13800138000", "nickname": "张三"}
// 响应: TokenResponse (同上)
```

---

## 2. 门店与房型 `/api/hotels`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/hotels` | 否 | `{code, data: {total, items}}` | 门店列表(分页,筛选) |
| GET | `/api/hotels/{hotel_id}` | 否 | 裸 HotelDetail | 门店详情(含房型) |
| GET | `/api/hotels/{hotel_id}/rooms` | 否 | 裸 list[RoomOut] | 门店房型列表 |
| GET | `/api/hotels/rooms/{room_id}` | 否 | 裸 RoomOut | 房型详情 |
| POST | `/api/hotels` | 是(admin) | `{code, data, msg}` | 新增门店 |
| PUT | `/api/hotels/{hotel_id}` | 是(admin) | `{code, data, msg}` | 编辑门店 |
| DELETE | `/api/hotels/{hotel_id}` | 是(admin) | `{code, msg}` | 删除门店(软删除) |
| POST | `/api/hotels/{hotel_id}/rooms` | 是(admin) | `{code, data, msg}` | 新增房型 |
| PUT | `/api/hotels/rooms/{room_id}` | 是(admin) | `{code, data, msg}` | 编辑房型 |
| DELETE | `/api/hotels/rooms/{room_id}` | 是(admin) | `{code, msg}` | 删除房型(软删除) |

### 查询参数

`GET /api/hotels`:
- `city` - 按城市筛选
- `keyword` - 搜索关键词(名称/地址)
- `page` - 页码(默认1)
- `page_size` - 每页条数(默认20, 最大100)

---

## 3. 房态管理 `/api/rooms`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/rooms/status` | 是 | 裸 RoomStatusResponse | 房态总览(按门店) |

### 查询参数
- `hotel_id` - 门店ID(可选，不传返回全部)

### 响应字段
```json
{
  "hotel_id": 1,
  "hotel_name": "伊家人·西湖旗舰店",
  "total_rooms": 145,
  "available_total": 100,
  "booked_total": 5,
  "occupied_total": 20,
  "cleaning_total": 20,
  "items": [{...}]
}
```

---

## 4. 订单管理 `/api/orders`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| POST | `/api/orders` | 是 | 裸 OrderOut (201) | 创建订单 |
| GET | `/api/orders` | 是 | 裸 OrderListResponse | 订单列表(分页,筛选) |
| GET | `/api/orders/{order_id}` | 是 | 裸 OrderOut | 订单详情 |
| POST | `/api/orders/{order_id}/cancel` | 是 | 裸 OrderOut | 取消订单 |
| POST | `/api/orders/{order_id}/status` | 是(admin/front_desk) | 裸 OrderOut | 管理员更新状态 |

### 状态机

```
pending → paid → checked_in → completed
   ↓        ↓         ↓
cancelled  refunded  (不可取消/退款)
```

### 创建订单请求
```json
{
  "hotel_id": 1,
  "room_id": 3,
  "room_count": 1,
  "checkin_date": "2026-06-15",
  "checkout_date": "2026-06-17",
  "guest_name": "张三",
  "guest_phone": "13800138000",
  "remark": "无烟房"
}
```

### 查询参数
- `keyword` - 搜索订单号/客人姓名
- `status` - 订单状态筛选
- `start_date` / `end_date` - 日期范围(YYYY-MM-DD)
- `page` / `page_size`

---

## 5. 入住管理 `/api/checkin`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| POST | `/api/checkin/in` | 是 | 裸 CheckinOut | 办理入住 |
| POST | `/api/checkin/out/{checkin_id}` | 是 | 裸 CheckinOut | 办理退房 |
| GET | `/api/checkin` | 是 | 裸 CheckinListResponse | 入住记录列表 |
| GET | `/api/checkin/{checkin_id}` | 是 | 裸 CheckinOut | 入住详情 |
| POST | `/api/checkin/{checkin_id}/unlock` | 是 | 裸 CheckinOut | 记录开锁/关锁 |

### 入住请求
```json
{
  "order_id": 123,
  "room_number": "902"
}
```

### 开锁记录
```json
{
  "action": "unlock"  // unlock 或 lock
}
```

---

## 6. 保洁管理 `/api/cleaning`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| POST | `/api/cleaning/tasks` | 是(admin/front_desk/cleaner) | 裸 CleaningTaskOut | 创建保洁工单 |
| GET | `/api/cleaning/tasks` | 是 | 裸 TaskListResponse | 工单列表 |
| GET | `/api/cleaning/tasks/{task_id}` | 是 | 裸 CleaningTaskOut | 工单详情 |
| POST | `/api/cleaning/tasks/accept` | 是(cleaner/admin) | 裸 CleaningTaskOut | 保洁员接单 |
| POST | `/api/cleaning/tasks/start` | 是 | 裸 CleaningTaskOut | 开始清洁 |
| POST | `/api/cleaning/tasks/complete` | 是 | 裸 CleaningTaskOut | 完工打卡拍照 |
| GET | `/api/cleaning/my-tasks` | 是 | 裸 TaskListResponse | 我的工单(保洁员) |
| POST | `/api/cleaning/service` | 是 | 裸 ServiceRequestOut | 发起在店服务请求 |
| GET | `/api/cleaning/service` | 是 | 裸 ServiceListResponse | 服务请求列表 |
| GET | `/api/cleaning/service/{request_id}` | 是 | 裸 ServiceRequestOut | 服务请求详情 |
| POST | `/api/cleaning/service/{request_id}/accept` | 是(admin/front_desk/cleaner) | 裸 ServiceRequestOut | 接取服务 |
| POST | `/api/cleaning/service/{request_id}/complete` | 是 | 裸 ServiceRequestOut | 完成服务 |
| GET | `/api/cleaning/service-stats` | 是 | 裸 dict | 服务请求统计 |
| GET | `/api/cleaning/cleaners` | 是 | 裸 list | 保洁员列表+统计 |

### 在店服务类型
- `cleaning` - 呼叫保洁
- `delivery` - 送物
- `maintenance` - 维修报修
- `other` - 其他

### 工单状态
`pending → accepted → in_progress → completed`

---

## 7. 仪表盘 `/api/dashboard`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/dashboard/stats` | 是 | DashboardResponse `{code, data, msg}` | 完整统计 |
| GET | `/api/dashboard/activity` | 是 | ActivityResponse `{code, data, msg}` | 最近活动流 |
| GET | `/api/dashboard/perf` | 是 | `{code, data, msg}` | N+1优化性能对比 |

### 统计字段
- `total_rooms` / `occupied_rooms` / `occupancy_rate`
- `orders_today` / `revenue_today`
- `checked_in_count` / `pending_cleaning_count`
- `orders_yesterday` / `revenue_yesterday` (同比)
- `revenue_trend` (近7天) / `occupancy_trend` (近7天)

### 查询参数
- `hotel_id` - 门店筛选
- `limit` - 活动条数(activity端点, 默认20)

---

## 8. 财务管理 `/api/finance`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/finance/daily` | 是 | DailyRevenueResponse `{code, data, msg, summary}` | 日营收报表 |
| GET | `/api/finance/monthly` | 是 | MonthlyRevenueResponse `{code, data, msg}` | 月营收报表 |
| GET | `/api/finance/reconciliation` | 是 | ReconciliationResponse `{code, data, msg, summary}` | 支付对账 |
| GET | `/api/finance/overview` | 是 | `{code, data, msg}` | 财务总览 |

### 查询参数
`/api/finance/daily`: `start_date`, `end_date` (YYYY-MM-DD, 必填), `hotel_id` (可选)
`/api/finance/monthly`: `year`, `month` (必填), `hotel_id` (可选)
`/api/finance/reconciliation`: `start_date`, `end_date` (必填), `hotel_id`, `status`
`/api/finance/overview`: `hotel_id` (可选)

---

## 9. 设备管理 `/api/devices`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/devices/list` | 是 | DeviceListResponse `{code, data, total, ...}` | 设备列表 |
| GET | `/api/devices/stats` | 是 | `{code, data}` | 设备统计 |
| POST | `/api/devices/register` | 是(admin/front_desk) | DeviceDetailResponse `{code, data, msg}` | 注册设备 |
| POST | `/api/devices/heartbeat` | 是 | DeviceDetailResponse `{code, data, msg}` | 心跳上报 |
| GET | `/api/devices/{device_id}` | 是 | DeviceDetailResponse `{code, data, msg}` | 设备详情 |
| DELETE | `/api/devices/{device_id_str}` | 是(admin) | `{code, msg}` | 删除设备 |

### 设备类型
- `smart_lock` - 智能门锁
- `control_panel` - 客控面板
- `sensor` - 传感器
- `gateway` - 网关
- `charger` - 充电桩

---

## 10. 摄像头管理 `/api/cameras`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/cameras` | 是(admin) | `{code, data, total}` | 摄像头列表 |
| POST | `/api/cameras` | 是(admin) | `{code, data, msg}` | 添加摄像头 |
| GET | `/api/cameras/{camera_id}/stream` | 是(admin) | `{code, data}` | 获取RTSP流地址 |
| GET | `/api/cameras/{camera_id}/snapshot` | 是(admin) | JPEG图片流 | 获取摄像头快照 |
| PUT | `/api/cameras/{camera_id}` | 是(admin) | `{code, data, msg}` | 编辑摄像头 |
| DELETE | `/api/cameras/{camera_id}` | 是(admin) | `{code, msg}` | 删除摄像头 |

> 密码使用 XOR+base64 加密存储，通过 RTSP 协议获取视频流。snapshot 端点依赖 ffmpeg。

---

## 11. 微信支付 `/api/payment`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| POST | `/api/payment/create` | 是 | PayResponse `{code, data, msg}` | 创建支付(JSAPI下单) |
| POST | `/api/payment/notify` | 否(微信回调) | `{code, message}` | 支付结果通知 |
| GET | `/api/payment/query/{order_id}` | 是 | PayResponse `{code, data, msg}` | 查询支付状态 |
| POST | `/api/payment/refund` | 是 | PayResponse `{code, data, msg}` | 申请退款 |

> 当前为 Mock 实现，待微信商户号就位后接入真实支付。

---

## 12. 智能门锁 `/api/lock`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| POST | `/api/lock/unlock` | 是 | LockResponse `{code, data, msg}` | 开锁 |
| POST | `/api/lock/password` | 是 | LockResponse `{code, data, msg}` | 生成临时密码 |
| GET | `/api/lock/status/{checkin_id}` | 是 | LockResponse `{code, data, msg}` | 门锁状态 |
| GET | `/api/lock/info` | 否 | LockResponse `{code, data, msg}` | TTLock配置状态 |

> 对接 TTLock 通通酒店 API (https://api.ttlock.com/v3)

---

## 13. OTA 渠道对接 `/api/ota`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/ota/channels` | 是 | OTAResponse `{code, data, msg}` | 渠道列表 |
| POST | `/api/ota/channels` | 是 | OTAResponse `{code, data, msg}` | 添加渠道 |
| PUT | `/api/ota/channels/{channel}` | 是 | OTAResponse `{code, data, msg}` | 更新渠道 |
| DELETE | `/api/ota/channels/{channel}` | 是 | OTAResponse `{code, data, msg}` | 删除渠道 |
| POST | `/api/ota/sync/availability` | 是 | OTAResponse | 推送房态到渠道 |
| POST | `/api/ota/sync/auto` | 是 | OTAResponse | 自动同步所有渠道 |
| POST | `/api/ota/webhook/{channel}` | 否(OTA回调) | OTAResponse | 渠道订单回调 |
| POST | `/api/ota/sync/order-status` | 是 | OTAResponse | 反向同步订单状态 |

### 支持渠道
- `ctrip` - 携程
- `meituan` - 美团
- `fliggy` - 飞猪

> 当前为对接框架占位，审核通过后替换真实 API 地址。

---

## 14. 系统管理 `/api/system`

| 方法 | 路径 | 认证 | 响应格式 | 说明 |
|------|------|------|----------|------|
| GET | `/api/system/info` | 否 | `{code, data}` | 系统信息 |
| GET | `/api/system/errors` | 是 | `{code, data, total}` | 错误日志(最近50条) |
| GET | `/api/system/db-pool` | 是 | `{code, data}` | 连接池状态 |
| GET | `/api/system/backup-info` | 是 | `{code, data}` | 数据库备份信息 |
| GET | `/api/system/settings` | 是 | `{code, data}` | 获取系统设置 |
| POST | `/api/system/settings` | 是 | `{code, msg, data}` | 保存系统设置 |

---

## 15. 系统端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/` | 否 | 根路径 |
| GET | `/health` | 否 | 健康检查 |
| GET | `/docs` | 否 | Swagger UI |
| GET | `/openapi.json` | 否 | OpenAPI 规范 |

---

## 附录: 响应格式一致性分析

### 格式A: 统一包裹 `{code, data, msg}` (CRUD / 管理类)

| 模块 | 端点数量 |
|------|----------|
| hotels (CRUD) | 10 |
| devices | 6 |
| cameras | 6 |
| dashboard | 3 |
| finance | 4 |
| system | 6 |
| payment | 4 |
| ota | 8 |
| lock | 4 |
| auth (list_users) | 1 |

**小计: 52 个端点**

### 格式B: 裸对象 (查询/业务流)

| 模块 | 端点数量 |
|------|----------|
| auth (login/register/me/wx) | 5 |
| hotels (detail/rooms) | 3 |
| rooms (status) | 1 |
| orders (全部) | 5 |
| checkin (全部) | 5 |
| cleaning (全部) | 14 |

**小计: 33 个端点**

### 潜在改进
1. 格式B的端点中，orders/checkin 是核心业务流，为了前端便利维持裸对象返回也有合理性
2. 真正的裸dict/list返回 (cleaning.service-stats, cleaning.cleaners) 是边界情况，缺少统一错误格式
3. 建议长期统一为格式A，通过中间件或响应模型标准化

---

## 测试覆盖

- api_test.py: 101 个 pytest 用例
- e2e_full_test.py: 37 个端到端测试用例
- 合计: 138 个测试目标 (130基础 + 8额外扩展)
