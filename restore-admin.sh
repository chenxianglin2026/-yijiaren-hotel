#!/bin/bash
# 伊家人管理后台一键恢复脚本
# 用法: bash restore-admin.sh
set -e
echo "=== 伊家人管理后台恢复 ==="

# 服务器信息
SERVER="ubuntu@111.229.30.253"
PASS="yjr4001889468YJR"
BACKEND_DIR="/home/ubuntu/yijiaren/code/backend"
ADMIN_DIR="/home/ubuntu/yijiaren/code/admin"

# 从 GitHub 拉最新代码
echo "1/4 拉取代码..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$SERVER" \
  "cd /home/ubuntu/yijiaren/code && git pull origin main"

# 重启后端
echo "2/4 重启后端..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$SERVER" \
  "fuser -k 8001/tcp 2>/dev/null; sleep 1; cd $BACKEND_DIR && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/yijiaren.log 2>&1 &"

# 验证
sleep 3
echo "3/4 验证..."
curl -sk -o /dev/null -w "  后端: %{http_code}\n" https://7yijia888.com/
curl -sk -o /dev/null -w "  admin: %{http_code}\n" https://7yijia888.com/admin/
curl -sk -o /dev/null -w "  orders: %{http_code}\n" https://7yijia888.com/admin/pages/orders.html

echo "4/4 完成!"
echo "访问: https://7yijia888.com/admin/"
echo "账号: admin / admin123"
