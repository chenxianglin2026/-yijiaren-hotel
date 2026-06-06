# Project: 伊家人 — 无人智慧酒店系统

## Tech Stack
- 前端: 微信小程序 (10页) + PC管理后台 (HTML/CSS/SCSS)
- 后端: Python FastAPI, 20+ API 端点
- 数据库: SQLite (dev) / PostgreSQL (prod), 已固化到 VPS 宿主机 /data/yijiaren-db/
- 部署: Docker + Nginx, Tencent Cloud VPS 43.163.5.90:80→8001
- 门锁: TTLock 通通酒店 (open.ttlock.com, API: api.ttlock.com/v3)
- 公众号: 伊家科技智慧系统 (gh_279792ae7513, AppID wxc14bd70186a79479)
- 充电桩: washpayer.com 网页版 (死命令不可改)
- 微信支付: 待商户号
- OTA: 携程/美团/飞猪对接框架已完成
- 微信回调: wx_v4.py (端口 8003)

## Rules
- 小程序 AppID: wx15932207fb03a5a4, AppSecret: ***
- 管理后台 root = /app/admin, nginx 分发 /api 到 uvicorn:8000
- 测试 admin / admin123
- 代码在 ~/projects/yijiaren/code/
- 代码与文档分别建档, Git 管理
- 公众号充电桩菜单原封不动, 只能通过 API 操作
- DEV_MODE=True 用 SQLite, False 用 PostgreSQL
- VPS 微信回调端口 8003, 通过 nginx 代理到 /wechat
- Python 关键字: lat/lng/enabled (非 latitude/longitude/enable)
- Docker 容器名: yijiaren-app, 镜像 yjr, 数据卷 /data/yijiaren-db
- OpenClaw 网关: ws://127.0.0.1:18789, mode=local
- 团队手册: TEAM_HANDBOOK.md

## Style
- 暖金色酒店主题 (#c8a052)
- 中文字体 PingFang SC / Microsoft YaHei
- 小程序适老化 ×1.4
- commit 格式: type: 描述 (feat/fix/test/refactor/docs)
- 汇报: bullet points, 只用结果, 不要表格和长篇
- 开发自主推进, 不需请示
