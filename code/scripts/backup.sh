#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 伊家人酒店系统 - 数据库备份脚本
# 用法: ./backup.sh [--vps] [--local]
#
# 备份策略:
#   - 开发模式(SQLite): 直接复制 .db 文件到备份目录
#   - 生产模式(PostgreSQL): docker exec pg_dump
#   - 保留最近 30 天的备份，自动清理过期文件
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

VPS_HOST="${VPS_HOST:-43.163.5.90}"
VPS_USER="${VPS_USER:-root}"
VPS_PATH="${VPS_PATH:-/root/yijiaren}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
TARGET="local"

# ── 参数解析 ──────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --vps)   TARGET="vps" ;;
        --local) TARGET="local" ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

mkdir -p "$BACKUP_DIR"

echo "═══════════════════════════════════════════════"
echo "  伊家人数据库备份"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  目标: $TARGET"
echo "═══════════════════════════════════════════════"

# ── 本地备份 ──────────────────────────────────────────
if [ "$TARGET" = "local" ]; then
    DB_FILE="$PROJECT_DIR/backend/data/yijiaren.db"
    BACKUP_FILE="$BACKUP_DIR/yijiaren_${TIMESTAMP}.db"

    if [ -f "$DB_FILE" ]; then
        DB_SIZE=$(stat -f%z "$DB_FILE" 2>/dev/null || stat -c%s "$DB_FILE" 2>/dev/null || echo 0)
        cp "$DB_FILE" "$BACKUP_FILE"
        echo "  ✅ SQLite 数据库已备份"
        echo "     源文件: $DB_FILE"
        echo "     大小: $(numfmt --to=iec $DB_SIZE 2>/dev/null || echo "${DB_SIZE} bytes")"
        echo "     备份到: $BACKUP_FILE"
    else
        echo "  ⚠️  本地 SQLite 数据库不存在: $DB_FILE"
        echo "     如使用 PostgreSQL，请用 --vps 参数备份远程"
    fi
fi

# ── VPS 备份 ──────────────────────────────────────────
if [ "$TARGET" = "vps" ]; then
    echo "  → 连接到 VPS: $VPS_USER@$VPS_HOST"

    # 检查 VPS 上是否使用 SQLite 或 PostgreSQL
    ssh "$VPS_USER@$VPS_HOST" bash <<'VSSH'
set -e
BACKUP_DIR="/root/yijiaren-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# 检查容器状态
if docker ps --format '{{.Names}}' | grep -q "yijiaren-postgres"; then
    echo "  → PostgreSQL 模式备份..."
    docker exec yijiaren-postgres pg_dump -U yijiaren yijiaren > "$BACKUP_DIR/yijiaren_pg_${TIMESTAMP}.sql"
    echo "  ✅ PostgreSQL 备份完成: yijiaren_pg_${TIMESTAMP}.sql"
elif [ -f /data/yijiaren-db/yijiaren.db ]; then
    echo "  → SQLite 模式备份..."
    cp /data/yijiaren-db/yijiaren.db "$BACKUP_DIR/yijiaren_${TIMESTAMP}.db"
    echo "  ✅ SQLite 备份完成: yijiaren_${TIMESTAMP}.db"
else
    # 尝试从容器内获取 SQLite
    echo "  → 尝试从容器获取 SQLite..."
    docker cp yijiaren-app:/app/data/yijiaren.db "$BACKUP_DIR/yijiaren_${TIMESTAMP}.db" 2>/dev/null && \
        echo "  ✅ 从容器备份完成" || \
        echo "  ⚠️  未找到数据库文件"
fi
VSSH

    # 拉取备份到本地
    echo ""
    echo "  → 拉取备份到本地..."
    scp "$VPS_USER@$VPS_HOST:/root/yijiaren-backups/yijiaren_${TIMESTAMP}.*" "$BACKUP_DIR/" 2>/dev/null && \
        echo "  ✅ 备份已拉取到本地: $BACKUP_DIR/" || \
        echo "  ⚠️  拉取失败，备份保留在 VPS"
fi

# ── 清理过期备份 ─────────────────────────────────────
echo ""
echo "  → 清理过期备份 (保留 ${RETENTION_DAYS} 天)..."
DELETED=$(find "$BACKUP_DIR" -name "yijiaren_*.db" -mtime +${RETENTION_DAYS} -delete -print 2>/dev/null | wc -l)
DELETED_SQL=$(find "$BACKUP_DIR" -name "yijiaren_pg_*.sql" -mtime +${RETENTION_DAYS} -delete -print 2>/dev/null | wc -l)
echo "  ✅ 清理完成 (删除 .db: $DELETED, .sql: $DELETED_SQL)"

# ── 备份清单 ──────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  备份目录: $BACKUP_DIR"
echo "  现有备份:"
ls -lh "$BACKUP_DIR"/yijiaren_* 2>/dev/null | tail -5 || echo "    (无备份文件)"
echo "═══════════════════════════════════════════════"
