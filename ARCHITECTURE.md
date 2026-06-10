# 伊家人酒店系统 - 项目架构

> 最后更新: 2026-06-09

## 技术栈

- 后端: Python FastAPI + SQLite (dev) / PostgreSQL (prod)
- 前端: 微信小程序 (10 页面) + 管理后台 (13 页面 HTML/CSS/JS)
- 部署: Docker 单容器 (nginx + uvicorn)
- VPS: 43.163.5.90:80 → container:8001
- 主题色: #c8a052 (暖金色)

## 目录结构

```
code/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── db.py            # 数据模型 (User, Hotel, Room, Order, Device...)
│   │   ├── config.py        # 配置
│   │   └── api/
│   │       ├── auth.py      # 认证 (login/register/wx-login/me)
│   │       ├── hotels.py    # 门店+房型 CRUD
│   │       ├── rooms.py     # 房型管理
│   │       ├── orders.py    # 订单管理
│   │       ├── devices.py   # 设备管理
│   │       ├── cleaning.py  # 保洁管理
│   │       ├── cameras.py   # 海康威视摄像头
│   │       ├── ota.py       # OTA 渠道对接
│   │       ├── dashboard.py # 监控看板
│   │       ├── system.py    # 系统信息/DB连接池
│   │       └── finance.py   # 财务报表
│   ├── tests/
│   │   ├── api_test.py      # API 测试 (58)
│   │   └── e2e_full_test.py # 端到端测试 (29)
│   └── seed_mock.py         # 种子数据
├── admin/                   # 管理后台 (13 页面)
├── miniapp/                 # 微信小程序 (10 页面)
│   ├── app.js
│   ├── utils/api.js         # API 封装
│   └── pages/
├── docs/                    # 文档
└── scripts/                 # 运维脚本
```

## 核心约定

- 关键字: lat/lng/enabled (非 latitude/longitude/enable)
- 测试账号: admin/admin123
- DEV_MODE: true=SQLite, false=PostgreSQL
- Docker 容器: yijiaren-app, 镜像 yjr
- 数据目录: /data/yijiaren-db (宿主机持久化)

## 外部依赖

| 依赖 | 状态 |
|------|------|
| 微信小程序 AppID | wx15932207fb03a5a4 |
| 微信支付 | 待商户号 |
| TTLock 门锁 | 待审核 |
| OTA 渠道 | 框架完成 |
| 充电桩 | 未对接 |
