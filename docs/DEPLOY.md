# 伊家人酒店系统 — 部署手册

## 公网地址
- 管理后台: http://43.163.5.90:8001
- API: http://43.163.5.90:8001/api/

## 登录
- 用户名: admin
- 密码: admin123
- 重启后自动创建，无需手动干预

## VPS 架构
```
Docker: yijiaren-app (nginx + uvicorn)
  ├── nginx :8001 → /app/admin/ (静态管理后台)
  │                 /api/ → uvicorn:8000 (后端)
  │                 /wechat → 宿主机:8003 (微信回调)
  └── uvicorn :8000 → FastAPI + SQLite
```

## 部署命令
```bash
ssh root@43.163.5.90
cd /root/yijiaren/backend
docker build -t yjr .
docker rm -f yijiaren-app
docker run -d --name yijiaren-app -p 8001:8001 --restart unless-stopped yjr
```

## 更新
```bash
rsync -avz ~/projects/yijiaren/code/backend/ root@43.163.5.90:/root/yijiaren/backend/
rsync -avz ~/projects/yijiaren/code/admin/ root@43.163.5.90:/root/yijiaren/backend/admin/
# 然后执行上面部署命令
```

## 微信回调
- URL: http://43.163.5.90:8001/wechat
- Token: 15f14ed3cac8f82fe97e24b975c7c9dc
- 加密方式: 明文模式
