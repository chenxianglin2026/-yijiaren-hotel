#!/bin/bash
#
# 伊家人 VPS 健康检查脚本
# 用法: bash scripts/healthcheck.sh
#
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/yijiaren}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${NC} $1 — $2"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1 — $2"; }

echo "═══════════════════════════════════════"
echo "  伊家人 VPS 健康检查"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════"
echo ""

# ── 1. Docker 服务状态 ──
echo "【Docker 容器状态】"
if ! systemctl is-active --quiet docker 2>/dev/null; then
    fail "Docker 服务" "未运行"
else
    pass "Docker 服务运行中"
fi

cd "$PROJECT_DIR" 2>/dev/null || { fail "项目目录" "不存在: $PROJECT_DIR"; }

for container in yijiaren-postgres yijiaren-app yijiaren-nginx; do
    if docker compose ps "$container" 2>/dev/null | grep -q "Up"; then
        pass "$container 运行中"
    else
        fail "$container" "未运行或异常"
    fi
done

echo ""

# ── 2. PostgreSQL 数据库检查 ──
echo "【PostgreSQL 数据库】"
if docker compose exec -T postgres pg_isready -U yijiaren -d yijiaren &>/dev/null; then
    pass "PostgreSQL 连接正常"

    # 检查数据量
    ROW_COUNT=$(docker compose exec -T postgres psql -U yijiaren -d yijiaren -t -c \
        "SELECT sum(n_live_tup) FROM pg_stat_user_tables;" 2>/dev/null | tr -d ' ' || echo "0")
    pass "活跃数据行: ${ROW_COUNT:-0}"
else
    fail "PostgreSQL" "无法连接"
fi

echo ""

# ── 3. 应用 API 健康端点 ──
echo "【FastAPI 应用】"
APP_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$APP_HEALTH" = "200" ]; then
    RESP=$(curl -s --max-time 10 http://localhost:8000/health 2>/dev/null)
    pass "FastAPI /health → 200"
    pass "响应: $RESP"
else
    fail "FastAPI /health" "HTTP $APP_HEALTH"
fi

echo ""

# ── 4. Nginx 反向代理检查 ──
echo "【Nginx 反向代理】"
NGINX_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost/health 2>/dev/null || echo "000")
if [ "$NGINX_HEALTH" = "200" ]; then
    pass "Nginx → app /health → 200"
else
    fail "Nginx /health" "HTTP $NGINX_HEALTH"
fi

WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost/ 2>/dev/null || echo "000")
if [ "$WEB_STATUS" = "200" ]; then
    pass "管理后台 / → 200"
else
    warn "管理后台 /" "HTTP $WEB_STATUS"
fi

echo ""

# ── 5. 磁盘使用 ──
echo "【磁盘空间】"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
ROOT_FREE=$(df -h / | awk 'NR==2 {print $4}')
if [ "$DISK_USAGE" -gt 90 ]; then
    fail "根分区使用率" "${DISK_USAGE}% (剩余 ${ROOT_FREE})"
elif [ "$DISK_USAGE" -gt 80 ]; then
    warn "根分区使用率" "${DISK_USAGE}% (剩余 ${ROOT_FREE})"
else
    pass "根分区使用率: ${DISK_USAGE}% (剩余 ${ROOT_FREE})"
fi

# 备份目录
if [ -d /opt/backups/yijiaren ]; then
    BACKUP_SIZE=$(du -sh /opt/backups/yijiaren 2>/dev/null | cut -f1)
    BACKUP_COUNT=$(find /opt/backups/yijiaren -name "backup_*.sql.gz" 2>/dev/null | wc -l | tr -d ' ')
    pass "备份目录: ${BACKUP_COUNT} 个文件, ${BACKUP_SIZE}"
else
    warn "备份目录" "不存在 /opt/backups/yijiaren"
fi

echo ""

# ── 6. 内存使用 ──
echo "【系统内存】"
MEM_TOTAL=$(free -m | awk 'NR==2 {print $2}')
MEM_USED=$(free -m | awk 'NR==2 {print $3}')
MEM_PCT=$((MEM_USED * 100 / MEM_TOTAL))
if [ "$MEM_PCT" -gt 90 ]; then
    fail "内存使用率" "${MEM_PCT}% (${MEM_USED}MB / ${MEM_TOTAL}MB)"
elif [ "$MEM_PCT" -gt 80 ]; then
    warn "内存使用率" "${MEM_PCT}% (${MEM_USED}MB / ${MEM_TOTAL}MB)"
else
    pass "内存使用率: ${MEM_PCT}% (${MEM_USED}MB / ${MEM_TOTAL}MB)"
fi

# Docker 容器内存
for container in yijiaren-postgres yijiaren-app yijiaren-nginx; do
    MEM=$(docker stats --no-stream --format "{{.MemUsage}}" "$container" 2>/dev/null | cut -d'/' -f1)
    if [ -n "$MEM" ]; then
        pass "$container 内存: $MEM"
    fi
done

echo ""

# ── 7. 上次备份时间 ──
echo "【数据备份】"]
LATEST_BACKUP=$(find /opt/backups/yijiaren -name "backup_*.sql.gz" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
if [ -n "$LATEST_BACKUP" ]; then
    BACKUP_AGE=$(find "$LATEST_BACKUP" -mmin +1440 -print 2>/dev/null | wc -l | tr -d ' ')
    if [ "$BACKUP_AGE" -gt 0 ]; then
        warn "上次备份超过 24 小时" "$(basename "$LATEST_BACKUP")"
    else
        pass "最近备份: $(basename "$LATEST_BACKUP")"
    fi
else
    warn "未找到备份文件" ""
fi

echo ""
echo "═══════════════════════════════════════"
echo -e "  结果: ${GREEN}${PASS} 通过${NC} / ${RED}${FAIL} 失败${NC}"
echo "═══════════════════════════════════════"

exit $FAIL
