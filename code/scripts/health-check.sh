#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 伊家人酒店系统 - 生产环境健康检查
# 用法: ./health-check.sh [--vps] [--local]
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

VPS_HOST="${VPS_HOST:-43.163.5.90}"
VPS_USER="${VPS_USER:-root}"
BASE_URL="http://localhost:8001"
TARGET="local"
FAILED=0
PASSED=0

for arg in "$@"; do
    case "$arg" in
        --vps)   TARGET="vps"; BASE_URL="http://${VPS_HOST}" ;;
        --local) TARGET="local" ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

pass() { PASSED=$((PASSED+1)); echo "  ✅ $1"; }
fail() { FAILED=$((FAILED+1)); echo "  ❌ $1"; }

echo "═══════════════════════════════════════════════"
echo "  伊家人生产环境健康检查"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  目标: $BASE_URL"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. 基础可达性 ──
echo "── [1] 基础可达性 ──"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$BASE_URL/health" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    pass "健康检查 HTTP $HTTP_CODE"
else
    fail "健康检查 HTTP $HTTP_CODE (预期200)"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$BASE_URL/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    pass "根路径 HTTP $HTTP_CODE"
else
    fail "根路径 HTTP $HTTP_CODE (预期200)"
fi

# ── 2. API 响应格式 ──
echo ""
echo "── [2] API 响应格式 ──"

# 酒店列表
RESP=$(curl -s --connect-timeout 5 "$BASE_URL/api/hotels" 2>/dev/null || echo "{}")
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'data' in d" 2>/dev/null; then
    pass "GET /api/hotels 响应格式正确"
else
    fail "GET /api/hotels 响应格式异常"
fi

# 认证 - 获取 TOKEN
RESP=$(curl -s -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' \
    --connect-timeout 5 2>/dev/null || echo "{}")
TOKEN=""
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'access_token' in d" 2>/dev/null; then
    TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    pass "POST /api/auth/login 认证成功"
else
    fail "POST /api/auth/login 认证失败"
fi

# 仪表盘 (需要认证)
if [ -n "$TOKEN" ]; then
    RESP=$(curl -s --connect-timeout 5 "$BASE_URL/api/dashboard/stats" \
        -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "{}")
    if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('code')==0" 2>/dev/null; then
        pass "GET /api/dashboard/stats 响应格式正确"
    else
        fail "GET /api/dashboard/stats 响应异常"
    fi

    # 系统信息
    RESP=$(curl -s --connect-timeout 5 "$BASE_URL/api/system/info" 2>/dev/null || echo "{}")
    if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('code')==0" 2>/dev/null; then
        V=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['version'])")
        D=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['db_type'])")
        pass "系统信息: v$V, DB=$D"
    else
        fail "系统信息获取失败"
    fi

    # 错误日志检查
    RESP=$(curl -s --connect-timeout 5 "$BASE_URL/api/system/errors" \
        -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "{}")
    ERR_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "?")
    if [ "$ERR_COUNT" != "?" ]; then
        if [ "$ERR_COUNT" -eq 0 ]; then
            pass "错误日志: 0 条 (干净)"
        else
            echo "  ⚠️  错误日志: $ERR_COUNT 条 (最近5条):"
            echo "$RESP" | python3 -c "
import sys,json
for e in json.load(sys.stdin).get('data',[])[:5]:
    print(f'      [{e[\"ts\"][:19]}] {e[\"endpoint\"]}: {e[\"message\"][:80]}')
" 2>/dev/null || true
        fi
    fi
fi

# ── 3. 容器/进程状态 ──
echo ""
echo "── [3] 服务进程状态 ──"

if [ "$TARGET" = "local" ]; then
    if pgrep -f "uvicorn.*app.main" > /dev/null 2>&1; then
        PID=$(pgrep -f "uvicorn.*app.main" | head -1)
        pass "uvicorn 运行中 (PID: $PID)"
    else
        fail "uvicorn 未运行"
    fi
else
    ssh "${VPS_USER}@${VPS_HOST}" 'docker ps --filter "name=yijiaren" --format "  {{.Names}}: {{.Status}}"' 2>/dev/null || \
        fail "Docker 不可达"
fi

# ── 4. HTTPS/SSL 检查 ──
if [ "$TARGET" = "vps" ]; then
    echo ""
    echo "── [4] HTTPS/SSL 检查 ──"
    if echo | openssl s_client -connect "${VPS_HOST}:443" -servername "${VPS_HOST}" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null; then
        pass "HTTPS 证书有效"
    else
        echo "  ⚠️  HTTPS 端口 443 无有效证书"
        echo "     运行: certbot --nginx -d www.yijiaren.com"
    fi
fi

# ── 5. 响应时间 ──
echo ""
echo "── [5] 响应时间基准 ──"
for ep in "/health" "/api/hotels" "/"; do
    T=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout 10 "$BASE_URL$ep" 2>/dev/null || echo "0")
    echo "  GET $ep: $(echo "$T * 1000" | bc 2>/dev/null || echo '?')ms"
done

# ── 总结 ──
echo ""
echo "═══════════════════════════════════════════════"
if [ "$FAILED" -eq 0 ]; then
    echo "  ✅ 全部通过 ($PASSED 项)"
else
    echo "  ⚠️  $PASSED 通过 / $FAILED 失败"
fi
echo "═══════════════════════════════════════════════"
exit $FAILED
