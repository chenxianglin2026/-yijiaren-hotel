#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 伊家人酒店系统 - 快速重启脚本
# 用法: ./restart.sh [--local] [--vps]
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

VPS_HOST="${VPS_HOST:-43.163.5.90}"
VPS_USER="${VPS_USER:-root}"
VPS_PATH="${VPS_PATH:-/root/yijiaren}"
TARGET="local"

for arg in "$@"; do
    case "$arg" in
        --vps)   TARGET="vps" ;;
        --local) TARGET="local" ;;
        *) echo "用法: $0 [--local|--vps]"; exit 1 ;;
    esac
done

echo "═══════════════════════════════════════════════"
echo "  伊家人酒店系统 - 重启"
echo "  目标: $TARGET"
echo "═══════════════════════════════════════════════"

if [ "$TARGET" = "local" ]; then
    echo ""
    echo "[1/3] 停止本地服务..."
    pkill -f "uvicorn.*app.main" 2>/dev/null && echo "  ✅ 已停止" || echo "  ℹ️  无运行中进程"

    echo "[2/3] 重置测试数据..."
    cd "$(dirname "$0")/../backend"
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    python seed_mock.py --force 2>/dev/null && echo "  ✅ 种子数据已重置" || echo "  ⚠️  种子数据重置失败"

    echo "[3/3] 启动服务..."
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
    sleep 2

    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "  ✅ 服务已启动 http://localhost:8001"
    else
        echo "  ❌ 服务启动失败"
        exit 1
    fi
else
    echo ""
    echo "[1/2] 重启 Docker 容器..."
    ssh "${VPS_USER}@${VPS_HOST}" "cd ${VPS_PATH} && docker compose restart app nginx" 2>/dev/null || {
        echo "  ⚠️  compose restart 失败，尝试 docker 命令..."
        ssh "${VPS_USER}@${VPS_HOST}" "docker restart yijiaren-app yijiaren-nginx"
    }
    echo "  ✅ 容器已重启"

    echo "[2/2] 等待服务就绪..."
    for i in $(seq 1 15); do
        if ssh "${VPS_USER}@${VPS_HOST}" "curl -s http://localhost:8001/health" > /dev/null 2>&1; then
            echo "  ✅ 服务就绪"
            break
        fi
        sleep 2
    done
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ 重启完成"
echo "═══════════════════════════════════════════════"
