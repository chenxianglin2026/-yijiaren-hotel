# 伊家人酒店系统 — 部署文档

> 版本: v1.0
> 日期: 2026-06-06
> VPS: Tencent Cloud 新加坡一区 43.163.5.90
> 域名: www.yijiaren.com

---

## 一、架构概览

```
                         ┌─────────────────────────────────────┐
                         │         Tencent Cloud VPS           │
                         │         43.163.5.90                  │
                         │                                      │
  Internet ────► :80 ────┤  ┌──────────────────────────────┐   │
                         │  │  Nginx (yijiaren-nginx)       │   │
                         │  │  /api        → app:8000       │   │
                         │  │  /wechat     → host:8003      │   │
                         │  │  /docs       → app:8000       │   │
                         │  │  /health     → app:8000       │   │
                         │  │  /           → app:8000       │   │
                         │  └──────────────────────────────┘   │
                         │                                      │
                         │  ┌──────────────────────────────┐   │
                         │  │  FastAPI (yijiaren-app)       │   │
                         │  │  uvicorn :8000               │   │
                         │  │  20+ API 端点                 │   │
                         │  └───────────┬──────────────────┘   │
                         │              │                       │
                         │  ┌───────────▼──────────────────┐   │
                         │  │  PostgreSQL (yijiaren-postgres)│   │
                         │  │  :5432 (仅本地 127.0.0.1)     │   │
                         │  └──────────────────────────────┘   │
                         │                                      │
                         │  ┌──────────────────────────────┐   │
                         │  │  wx_v4.py (宿主机 :8003)      │   │
                         │  │  微信回调服务器               │   │
                         │  └──────────────────────────────┘   │
                         └─────────────────────────────────────┘
```

容器列表:
| 容器名 | 镜像 | 端口 | 职责 |
|--------|------|------|------|
| yijiaren-nginx | nginx:alpine | 80:80 | 反向代理 + 静态文件 |
| yijiaren-app | yjr:latest | 8000 (内部) | FastAPI 后端 |
| yijiaren-postgres | postgres:16-alpine | 127.0.0.1:5432 | 数据库 |

---

## 二、环境要求

### VPS 最低配置
- OS: Ubuntu 22.04+ / Debian 12+
- CPU: 2 核
- RAM: 4 GB (PostgreSQL 会占用缓存)
- 磁盘: 40 GB SSD
- 已安装: Docker 24+, Docker Compose v2

### 安装 Docker (首次部署)
```bash
# 官方脚本
curl -fsSL https://get.docker.com | bash

# 启动并设置开机自启
sudo systemctl enable docker
sudo systemctl start docker

# 验证
docker --version
docker compose version
```

---

## 三、首次部署

### 1. 拉取代码
```bash
mkdir -p /opt/yijiaren
cd /opt/yijiaren
git clone <repo-url> .
# 或 rsync 本地代码到 VPS:
# rsync -avz ~/projects/yijiaren/code/ root@43.163.5.90:/opt/yijiaren/
```

### 2. 配置环境变量
```bash
cd /opt/yijiaren
cp .env.example .env

# 编辑 .env, 至少修改以下项:
vim .env
```

必填环境变量:
| 变量 | 说明 | 示例值 |
|------|------|--------|
| SECRET_KEY | JWT 签名密钥 (随机生成) | `openssl rand -hex 32` |
| DEV_MODE | 置 false 使用 PostgreSQL | false |
| WX_APPID | 小程序 AppID | wx15932207fb03a5a4 |
| WX_SECRET | 小程序 AppSecret | (从微信后台获取) |
| TTLOCK_CLIENT_ID | 门锁平台 Client ID | (从 open.ttlock.com 获取) |
| TTLOCK_CLIENT_SECRET | 门锁平台 Client Secret | (从 open.ttlock.com 获取) |
| SERVER_DOMAIN | 服务器域名 | https://www.yijiaren.com |

生成随机 SECRET_KEY:
```bash
openssl rand -hex 32
# 输出类似: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2
```

### 3. 构建镜像并启动
```bash
cd /opt/yijiaren
docker compose build
docker compose up -d

# 查看启动状态
docker compose ps
docker compose logs -f app
```

启动顺序: postgres → app → nginx (app 依赖 postgres health check 通过)

### 4. 验证部署
```bash
# 健康检查
curl http://localhost:8000/health
# 期望: {"status":"ok","app":"伊家人酒店系统","version":"1.0.0"}

# 通过 Nginx 访问
curl http://localhost/health

# API 文档
curl http://localhost/docs
# 浏览器打开: http://43.163.5.90/docs

# 管理后台
curl http://localhost/admin/
```

### 5. 初始化数据库 (仅首次)
```bash
# 如果使用 SQLite 开发模式 (DEV_MODE=true)，表会在启动时自动创建
# PostgreSQL 模式下，表也由 FastAPI lifespan 自动创建

# 如需手动 seed 测试数据:
docker compose exec app python seed_mock.py
```

---

## 四、Nginx 配置

配置文件: `nginx/nginx.conf`

### 路由规则
| 路径 | 转发目标 | 说明 |
|------|----------|------|
| /api | app:8000 | FastAPI 后端 API |
| /docs | app:8000 | Swagger 文档 |
| /openapi.json | app:8000 | OpenAPI schema |
| /health | app:8000 | 健康检查 |
| /wechat | host.docker.internal:8003 | 微信回调 |
| / | app:8000 | 管理后台 |

### 重载 Nginx
```bash
# 测试配置
docker compose exec nginx nginx -t

# 重载
docker compose exec nginx nginx -s reload
```

---

## 五、域名与 DNS

### DNS 解析
```
www.yijiaren.com.   A   43.163.5.90
```

如果使用 Cloudflare / 阿里云 DNS，添加 A 记录即可。

### 验证 DNS 生效
```bash
dig +short www.yijiaren.com
# 期望: 43.163.5.90
```

---

## 六、SSL / HTTPS 配置

使用 Let's Encrypt (Certbot) 获取免费 SSL 证书。

### 方案一: Certbot standalone (推荐)
```bash
# 安装 certbot
sudo apt update
sudo apt install -y certbot

# 先停止 nginx 容器释放 80 端口
docker compose stop nginx

# 申请证书
sudo certbot certonly --standalone -d www.yijiaren.com

# 证书位置:
# /etc/letsencrypt/live/www.yijiaren.com/fullchain.pem
# /etc/letsencrypt/live/www.yijiaren.com/privkey.pem

# 重启 nginx
docker compose start nginx
```

### 修改 nginx/nginx.conf 增加 SSL
在 `nginx/nginx.conf` 中新增 HTTPS server 块:
```nginx
server {
    listen 443 ssl http2;
    server_name www.yijiaren.com;

    ssl_certificate     /etc/letsencrypt/live/www.yijiaren.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.yijiaren.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # ... 同 HTTP server 的 location 配置
}

server {
    listen 80;
    server_name www.yijiaren.com;
    return 301 https://$host$request_uri;  # HTTP → HTTPS 重定向
}
```

更新 docker-compose.yml 挂载证书:
```yaml
  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt/live/www.yijiaren.com/fullchain.pem:/etc/ssl/certs/yijiaren.pem:ro
      - /etc/letsencrypt/live/www.yijiaren.com/privkey.pem:/etc/ssl/private/yijiaren.key:ro
```

### SSL 证书自动续期
```bash
# certbot 自动续期 timer
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# 验证 timer 状态
sudo systemctl status certbot.timer

# 手动测试续期
sudo certbot renew --dry-run
```

---

## 七、数据备份

### PostgreSQL 备份
```bash
# 创建备份目录
mkdir -p /opt/backups/yijiaren

# 从 Docker 容器内备份
docker compose exec postgres pg_dump -U yijiaren yijiaren > /opt/backups/yijiaren/backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩
gzip /opt/backups/yijiaren/backup_*.sql
```

### 自动备份脚本 (crontab)
```bash
# 创建备份脚本
cat > /opt/scripts/yijiaren_backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/yijiaren"
mkdir -p $BACKUP_DIR
cd /opt/yijiaren || exit 1
docker compose exec -T postgres pg_dump -U yijiaren yijiaren > "$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete   # 保留 7 天
find $BACKUP_DIR -name "backup_*.sql" | tail -n +8 | xargs -r gzip  # 压缩旧备份
EOF

chmod +x /opt/scripts/yijiaren_backup.sh

# 添加到 crontab, 凌晨 3 点执行
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/scripts/yijiaren_backup.sh >> /var/log/yijiaren_backup.log 2>&1") | crontab -
```

### 恢复备份
```bash
# 恢复到 Docker PostgreSQL
docker compose exec -T postgres psql -U yijiaren yijiaren < /opt/backups/yijiaren/backup_20260606_030000.sql
```

### Docker Volume 备份
```bash
# 备份整个 postgres_data volume
docker run --rm -v yijiaren_postgres_data:/data -v /opt/backups:/backup alpine tar czf /backup/yijiaren_pgdata_$(date +%Y%m%d).tar.gz -C /data .
```

---

## 八、微信回调部署

微信服务器回调需要在 VPS 宿主机运行独立的回调服务 (端口 8003)。

### 启动微信回调服务
```bash
# 在 VPS 宿主机上
cd /opt/yijiaren/backend
nohup python3 wx_v4.py > /var/log/yijiaren_wechat.log 2>&1 &

# 或使用 systemd 管理
sudo cat > /etc/systemd/system/yijiaren-wechat.service << 'EOF'
[Unit]
Description=伊家人微信回调服务
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/yijiaren/backend
ExecStart=/usr/bin/python3 wx_v4.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable yijiaren-wechat
sudo systemctl start yijiaren-wechat
```

### 验证
```bash
# 检查回调服务
curl http://localhost:8003/health

# 通过 nginx 代理访问
curl http://localhost/wechat
```

---

## 九、常用运维命令

### Docker 管理
```bash
# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f app        # app 日志
docker compose logs -f nginx      # nginx 日志
docker compose logs -f --tail=100 # 最近 100 行

# 重启服务
docker compose restart app
docker compose restart nginx

# 停止所有服务
docker compose down

# 完全重建 (删除 volume 则丢数据!)
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### 数据库操作
```bash
# 进入 psql
docker compose exec postgres psql -U yijiaren

# 查看表
\dt

# 查询示例
SELECT count(*) FROM users;
SELECT count(*) FROM orders;
```

### 监控
```bash
# 资源使用
docker stats

# 磁盘使用
df -h
docker system df

# 清理旧镜像/容器
docker system prune -f
```

---

## 十、故障排查

### 容器无法启动
```bash
# 查看详细错误
docker compose logs app
docker compose logs postgres

# 检查端口冲突
sudo ss -tlnp | grep -E '80|5432|8000'

# 手动启动调试
docker compose run --rm app bash
```

### 数据库连接失败
```bash
# 检查 postgres 是否健康
docker compose exec postgres pg_isready -U yijiaren

# 检查网络
docker compose exec app ping postgres

# 检查 DATABASE_URL
docker compose exec app env | grep DATABASE
```

### Nginx 502 Bad Gateway
```bash
# app 容器是否运行
docker compose ps app

# app 是否监听 8000
docker compose exec app bash -c "ss -tlnp | grep 8000"

# nginx 错误日志
docker compose logs nginx | grep error
```

### 性能问题
```bash
# 查看 PostgreSQL 慢查询
docker compose exec postgres psql -U yijiaren -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 查看 app 进程
docker compose top app
```

---

## 十一、版本更新流程

```bash
# 1. 拉取最新代码
cd /opt/yijiaren
git pull origin main

# 2. 重新构建镜像
docker compose build app

# 3. 滚动更新 (零停机)
docker compose up -d --no-deps app

# 4. 等待健康检查通过
sleep 5
curl http://localhost/health

# 5. 查看日志确认
docker compose logs -f --tail=50 app
```

---

## 十二、安全清单

- [ ] 修改默认 SECRET_KEY (必须)
- [ ] 修改 PostgreSQL 默认密码 POSTGRES_PASSWORD (必须)
- [ ] 配置 SSL/HTTPS (强烈建议)
- [ ] 防火墙仅开放 80/443 端口，5432/8000 仅限 127.0.0.1
- [ ] .env 文件权限 600 (`chmod 600 .env`)
- [ ] 定期更新基础镜像 (`docker compose pull`)
- [ ] 配置 fail2ban 防止暴力破解
- [ ] 开启 PostgreSQL SSL 连接 (生产环境)
