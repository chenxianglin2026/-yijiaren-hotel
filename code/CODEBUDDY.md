## Tech Stack
- 前端: 微信小程序 (10页) + PC管理后台 (HTML/CSS)
- 后端: Python FastAPI, 15+ API 端点
- 数据库: SQLite (dev) / PostgreSQL (prod)
- 部署: Docker + Nginx, Tencent Cloud VPS (43.163.5.90:8001)
- 公众号: 伊家科技智慧社区 (wx0b710cdc89537120)
- 公司: 东莞市伊家智能科技有限公司
- CSS: SCSS (sass-embedded)
## Rules
- 后端端口 8001

- 小程序 AppID: wx15932207fb03a5a4

- 管理后台 root = /app/admin, nginx 分发 /api 到 uvicorn:8000

- 测试 admin / admin123

- 代码在 ~/projects/yijiaren/code/

- Git 管理

- 管理后台 SCSS 修改后需 `npm run build` 重新编译

- 暂不支持微信支付 (V3 规划)

- 资金为商家代管模式, 对账人工

## Style
- 暖金色酒店主题 (#c8a052)

- 中文字体 PingFang SC / Microsoft YaHei

- 小程序适老化 ×1.4

- commit 简洁

