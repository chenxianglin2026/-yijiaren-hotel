#!/bin/bash
# 修复酒店首页乱码 - 部署正确 index.html 到 Docker 容器
# 在 Shanghai 服务器 111.229.30.253 上执行

set -e
echo "=== 修复酒店首页乱码 ==="

# 1. 拉取最新代码
cd /root/yijiaren 2>/dev/null || cd /root
git -C /root/yijiaren pull 2>/dev/null || echo "跳过 git pull，用本地文件"

# 2. 找到正确的 index.html
if [ -f /root/yijiaren/code/admin/index.html ]; then
  SRC=/root/yijiaren/code/admin/index.html
elif [ -f /root/yijiaren/backend/admin/index.html ]; then
  SRC=/root/yijiaren/backend/admin/index.html
else
  echo "ERROR: 找不到 index.html"; exit 1
fi

echo "源文件: $SRC"
head -3 "$SRC"

# 3. 复制到 Docker 容器
docker cp "$SRC" yijiaren-app:/app/admin/index.html 2>/dev/null && echo "docker cp OK"

# 4. 重载容器内 nginx
docker exec yijiaren-app nginx -s reload 2>/dev/null && echo "nginx reload OK"

# 5. 验证
sleep 1
RESULT=$(curl -sk --connect-timeout 3 https://127.0.0.1/ 2>/dev/null | head -1)
if echo "$RESULT" | grep -q "DOCTYPE"; then
  echo "✅ 修复成功 - 首页已包含完整HTML"
else
  echo "⚠️  请刷新浏览器验证: $RESULT"
fi
