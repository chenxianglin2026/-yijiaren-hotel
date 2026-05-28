# 伊家人酒店系统 — 开发流程

> 复用 KeepSafe 7步法 + TDD

## 开发七步

1. 需求确认 → 陈总一句话描述
2. 方案设计 → Hermes + OpenClaw 写方案 → designs/
3. 方案审批 → 陈总点头
4. 任务拆派 → Hermes → 子代理
5. 开发执行 → 子代理 TDD
6. 代码审查 → OpenClaw
7. 归档汇报 → Hermes 自动

## 代码规范

- 小程序: 微信原生框架, app.json pages 注册
- 后端: FastAPI Python, RESTful
- 后台: React/Vue + Ant Design
- 命名: 小驼峰 JS, 下划线 Python

## 密钥管理

- 所有密钥 {{PLACEHOLDER}}
- 真实密钥存 ~/.hermes/secrets/
- 永不进 Git
