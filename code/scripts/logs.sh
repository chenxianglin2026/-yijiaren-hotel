#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# 伊家人酒店系统 - 日志查看脚本
# 用法:
#   ./logs.sh              # 查看所有日志（tail -f）
#   ./logs.sh --app        # 仅应用日志
#   ./logs.sh --nginx      # 仅 nginx 日志
#   ./logs.sh --errors     # 查看错误日志
#   ./logs.sh --access     # 查看访问日志
#   ./logs.sh --vps        # VPS 日志
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

VPS_HOST="${VPS_HOST:-43.163.5.90}"
VPS_USER="${VPS_USER:-root}"
TARGET="local"
MODE="all"
LINES=100

for arg in "$@"; do
    case "$arg" in
        --vps)    TARGET="vps" ;;
        --app)    MODE="app" ;;
        --nginx)  MODE="nginx" ;;
        --errors) MODE="errors" ;;
        --access) MODE="access" ;;
        -n)       shift; LINES="$1" ;;
        *)        echo "用法: $0 [--vps] [--app|--nginx|--errors|--access] [-n N]"; exit 1 ;;
    esac
done

if [ "$TARGET" = "local" ]; then
    echo "═══════════════════════════════════════════════"
    echo "  查看本地日志"
    echo "═══════════════════════════════════════════════"
    
    case "$MODE" in
        app)
            # 找到 uvicorn 进程输出（如果有重定向到文件）
            if [ -f /tmp/yijiaren.log ]; then
                tail -n "$LINES" -f /tmp/yijiaren.log
            else
                echo "⚠️  未找到 /tmp/yijiaren.log"
                echo "   启动时使用: python -m uvicorn app.main:app ... > /tmp/yijiaren.log 2>&1"
            fi
            ;;
        errors)
            # 通过 API 查看错误日志
            TOKEN=*** -s -X POST http://localhost:8001/api/auth/login \
                -H "Content-Type: application/json" \
                -d '{"username":"admin","password":"admin123"}' 2>/dev/null \
                | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
            if [ -n "$TOKEN" ]; then
                curl -s "http://localhost:8001/api/system/errors" \
                    -H "Authorization: Bearer *** 2>/dev/null \
                    | python3 -m json.tool
            else
                echo "❌ 认证失败，无法获取错误日志"
            fi
            ;;
        *)
            echo "本地日志: 查看 uvicorn 终端输出或 /tmp/yijiaren.log"
            ;;
    esac
else
    echo "═══════════════════════════════════════════════"
    echo "  查看 VPS Docker 日志"
    echo "═══════════════════════════════════════════════"
    
    case "$MODE" in
        app)
            ssh "${VPS_USER}@${VPS_HOST}" "docker logs --tail ${LINES} -f yijiaren-app"
            ;;
        nginx)
            ssh "${VPS_USER}@${VPS_HOST}" "docker logs --tail ${LINES} -f yijiaren-nginx"
            ;;
        errors)
            ssh "${VPS_USER}@${VPS_HOST}" "docker logs --tail ${LINES} yijiaren-app 2>&1 | grep -iE 'error|exception|traceback|fail' | tail -20"
            ;;
        access)
            ssh "${VPS_USER}@${VPS_HOST}" "docker exec yijiaren-nginx cat /var/log/nginx/yijiaren_access.log | tail -${LINES}"
            ;;
        *)
            echo "  → 应用日志 (最近 20 行):"
            ssh "${VPS_USER}@${VPS_HOST}" "docker logs --tail 20 yijiaren-app"
            echo ""
            echo "  → Nginx 错误日志 (最近 10 行):"
            ssh "${VPS_USER}@${VPS_HOST}" "docker logs --tail 10 yijiaren-nginx"
            ;;
    esac
fi
