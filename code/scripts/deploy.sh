#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 伊家人酒店系统 - VPS 部署脚本
# 用法: ./deploy.sh [--rebuild] [--skip-tests]
#
# 从本地项目目录推送到 VPS 43.163.5.90 并重启 Docker 服务
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

VPS_HOST="${VPS_HOST:-43.163.5.90}"
VPS_USER="${VPS_USER:-root}"
VPS_PATH="${VPS_PATH:-/root/yijiaren}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REBUILD=false
SKIP_TESTS=false

# ── 参数解析 ──────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --rebuild)    REBUILD=true ;;
        --skip-tests) SKIP_TESTS=true ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

echo "═══════════════════════════════════════════════"
echo "  伊家人酒店系统 - 部署脚本"
echo "  目标: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo "═══════════════════════════════════════════════"

# ── 1. 运行本地测试 ──────────────────────────────────
if [ "$SKIP_TESTS" = false ]; then
    echo ""
    echo "[1/5] 运行本地测试..."
    cd "$PROJECT_DIR/backend"
    
    # 检查服务器是否在运行
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "  ✅ 服务器运行中"
    else
        echo "  ⚠️  服务器未运行，尝试启动..."
        source .venv/bin/activate 2>/dev/null || true
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
        sleep 3
    fi
    
    # 重置测试数据并运行 pytest
    echo "  → 运行 pytest (api_test.py)..."
    python -m pytest tests/api_test.py -v --tb=short -q 2>&1 | tail -5
    PYTESTS_EXIT=${PIPESTATUS[0]}
    
    echo "  → 运行 e2e 集成测试..."
    python tests/e2e_full_test.py 2>&1 | tail -5
    E2E_EXIT=${PIPESTATUS[0]}
    
    if [ "$PYTESTS_EXIT" -ne 0 ] || [ "$E2E_EXIT" -ne 0 ]; then
        echo "  ❌ 测试未全部通过，中止部署"
        echo "     pytest 退出码: $PYTESTS_EXIT"
        echo "     e2e 退出码:    $E2E_EXIT"
        exit 1
    fi
    echo "  ✅ 所有测试通过"
else
    echo "[1/5] ⏭️  跳过测试"
fi

# ── 2. 推送代码到 VPS ─────────────────────────────────
echo ""
echo "[2/5] 推送代码到 VPS..."
rsync -avz --delete \
    --exclude='.venv/' \
    --exclude='.pytest_cache/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='data/' \
    --exclude='node_modules/' \
    --exclude='.env' \
    --exclude='private.key' \
    "$PROJECT_DIR/" \
    "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "  ✅ 代码已推送"

# ── 3. 在 VPS 上重新构建/重启 ──────────────────────────
echo ""
echo "[3/5] VPS Docker 构建与重启..."

if [ "$REBUILD" = true ]; then
    echo "  → 重新构建镜像..."
    ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && docker compose build --no-cache app"
fi

# 重启服务
ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && docker compose up -d --force-recreate app nginx"

echo "  ✅ Docker 服务已重启"

# ── 4. 等待服务就绪 ──────────────────────────────────
echo ""
echo "[4/5] 等待服务就绪..."
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if ssh "$VPS_USER@$VPS_HOST" "curl -s http://localhost:8001/health" > /dev/null 2>&1; then
        echo "  ✅ 服务就绪 (${WAITED}s)"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo -n "."
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo "  ⚠️  服务启动超时，请手动检查"
fi

# ── 5. 生产健康检查 ──────────────────────────────────
echo ""
echo "[5/5] 生产环境健康检查..."
echo ""

# 通过 VPS 本地检查
ssh "$VPS_USER@$VPS_HOST" bash <<'VSSH'
echo "  → 容器状态:"
docker ps --filter "name=yijiaren" --format "    {{.Names}}: {{.Status}}"

echo ""
echo "  → API 健康检查:"
curl -s http://localhost:8001/health | python3 -m json.tool 2>/dev/null || echo "    ❌ 无法访问"

echo ""
echo "  → 外部访问检查:"
curl -s -o /dev/null -w "    HTTP %{http_code} (time: %{time_total}s)" http://localhost:80/health
echo ""

echo ""
echo "  → 磁盘使用:"
df -h / | tail -1

echo ""
echo "  → 内存使用:"
free -h | grep Mem
VSSH

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ 部署完成!"
echo "  API:  http://$VPS_HOST:80/api/"
echo "  文档: http://$VPS_HOST:80/docs"
echo "═══════════════════════════════════════════════"
