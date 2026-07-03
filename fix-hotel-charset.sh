#!/bin/bash
# 修复酒店首页乱码 - 适配 ubuntu 用户
set -e
echo "=== 修复酒店首页乱码 ==="

# 找到 yijiaren 代码位置
if [ -d /home/ubuntu/yijiaren ]; then
  YJ=/home/ubuntu/yijiaren
elif [ -d /root/yijiaren ]; then
  YJ=/root/yijiaren
else
  echo "ERROR: 找不到 yijiaren 目录"
  exit 1
fi
echo "yijiaren 目录: $YJ"

# 找 admin/index.html
SRC=""
[ -f "$YJ/code/admin/index.html" ] && SRC="$YJ/code/admin/index.html"
[ -f "$YJ/admin/index.html" ] && SRC="$YJ/admin/index.html"
[ -f "$YJ/backend/admin/index.html" ] && SRC="$YJ/backend/admin/index.html"

if [ -z "$SRC" ]; then
  echo "ERROR: 找不到 index.html"; exit 1
fi
echo "源文件: $SRC"
head -2 "$SRC"

# docker 权限
DOCKER="docker"
sudo docker ps >/dev/null 2>&1 && DOCKER="sudo docker" || true

echo "Docker: $DOCKER"

# 找容器名
CONTAINER=$($DOCKER ps --format '{{.Names}}' | grep -i yijiaren | head -1)
if [ -z "$CONTAINER" ]; then
  echo "ERROR: 找不到 yijiaren Docker 容器"
  $DOCKER ps --format '{{.Names}}'
  exit 1
fi
echo "容器: $CONTAINER"

# 复制文件
$DOCKER cp "$SRC" "$CONTAINER:/app/admin/index.html" && echo "docker cp OK"

# 重载 nginx
$DOCKER exec "$CONTAINER" nginx -s reload && echo "nginx reload OK"

# 验证
sleep 1
R=$(curl -sk --connect-timeout 3 https://127.0.0.1/ 2>/dev/null | head -1)
if echo "$R" | grep -q "DOCTYPE"; then
  echo "✅ 修复成功"
else
  echo "⚠️  请刷新浏览器: $R"
fi
