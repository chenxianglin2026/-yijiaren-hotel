#!/bin/bash
#
# 伊家人 VPS 数据库自动备份脚本
# 部署路径: /opt/yijiaren/scripts/backup.sh
# Crontab: 0 3 * * * /opt/yijiaren/scripts/backup.sh >> /var/log/yijiaren_backup.log 2>&1
#
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/yijiaren}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/yijiaren}"
RETENTION_DAYS=7
LOG_TAG="[backup]"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_TAG $*"; }

mkdir -p "$BACKUP_DIR"

# ── 1. PostgreSQL pg_dump（从 Docker 容器） ──
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

log "开始数据库备份 → ${DUMP_FILE}"
cd "$PROJECT_DIR" || { log "ERROR: 项目目录不存在: $PROJECT_DIR"; exit 1; }

if docker compose exec -T postgres pg_dump -U yijiaren yijiaren > "$DUMP_FILE" 2>/tmp/yijiaren_backup_err; then
    SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    log "备份成功 (${SIZE})"
else
    log "ERROR: pg_dump 失败"
    cat /tmp/yijiaren_backup_err
    exit 1
fi

# ── 2. 压缩 ──
gzip -f "$DUMP_FILE"
log "已压缩 → ${DUMP_FILE}.gz"

# ── 3. 清理旧备份（保留最近 ${RETENTION_DAYS} 天） ──
DELETED=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "清理 ${DELETED} 个过期备份 (>${RETENTION_DAYS}天)"
fi

# ── 4. 摘要 ──
COUNT=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" | wc -l)
DISK_USAGE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "备份目录: ${COUNT} 个文件, 共 ${DISK_USAGE}"

log "备份完成 ✓"
