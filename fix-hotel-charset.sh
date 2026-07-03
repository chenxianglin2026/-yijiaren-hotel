#!/bin/bash
echo "=== 开始修复 ==="
echo "用户: $(whoami)"

# 找目录
for d in /home/ubuntu/yijiaren /root/yijiaren; do
  [ -d "$d" ] && YJ="$d" && break
done
echo "YJ=$YJ"
if [ -z "$YJ" ]; then echo "失败: 找不到yijiaren目录"; ls /home/ubuntu/ /root/ 2>/dev/null; exit 1; fi

# 找index.html
for p in code/admin/index.html admin/index.html; do
  [ -f "$YJ/$p" ] && SRC="$YJ/$p" && break
done
echo "SRC=$SRC"
[ -z "$SRC" ] && echo "失败: 找不到index.html" && find "$YJ" -name index.html 2>/dev/null && exit 1

# docker
if docker ps >/dev/null 2>&1; then D="docker"
elif sudo docker ps >/dev/null 2>&1; then D="sudo docker"
else echo "失败: 无docker权限"; exit 1; fi
echo "DOCKER=$D"

CN=$($D ps --format '{{.Names}}' | grep -i yij | head -1)
echo "容器=$CN"
[ -z "$CN" ] && echo "失败: 找不到容器" && $D ps && exit 1

# 复制
$D cp "$SRC" "$CN:/app/admin/index.html" && echo "✅ docker cp OK" || { echo "❌ docker cp失败"; exit 1; }

# 重载
$D exec "$CN" nginx -s reload && echo "✅ nginx reload OK"

echo "=== 完成 ==="
