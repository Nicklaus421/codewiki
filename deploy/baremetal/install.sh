#!/usr/bin/env bash
# =============================================================
# 云核软件资产治理平台 —— 裸机安装脚本（Ubuntu/Debian/CentOS 类系统）
# 用法：sudo bash install.sh
# 前置：系统已安装 python3(>=3.10)、nodejs(>=20)、git、nginx
# =============================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/yunhe}"
APP_USER="${APP_USER:-yunhe}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "==> 安装目录：$APP_DIR，运行用户：$APP_USER"

# 1. 创建运行用户
if ! id "$APP_USER" &>/dev/null; then
  echo "==> 创建用户 $APP_USER"
  useradd -r -m -d "$APP_DIR" -s /usr/sbin/nologin "$APP_USER" || useradd -r -m -d "$APP_DIR" "$APP_USER"
fi
mkdir -p "$APP_DIR"/{backend,frontend,data}
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 2. 复制代码
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
echo "==> 从 $REPO_ROOT 复制代码"
rsync -a --delete "$REPO_ROOT/backend/" "$APP_DIR/backend/" 2>/dev/null || cp -r "$REPO_ROOT/backend/." "$APP_DIR/backend/"
rsync -a --delete "$REPO_ROOT/frontend/" "$APP_DIR/frontend/" 2>/dev/null || cp -r "$REPO_ROOT/frontend/." "$APP_DIR/frontend/"

# 3. 后端：虚拟环境 + 依赖
echo "==> 安装后端依赖"
cd "$APP_DIR/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
"$APP_DIR/backend/.venv/bin/pip" install --upgrade pip -q
"$APP_DIR/backend/.venv/bin/pip" install -r requirements.txt -q

# 4. 前端：构建产物
echo "==> 构建前端"
cd "$APP_DIR/frontend"
if [ ! -f package-lock.json ]; then
  npm install
else
  npm ci || npm install
fi
npm run build
rm -rf dist.bak 2>/dev/null || true

# 5. 环境变量
if [ ! -f "$APP_DIR/backend/.env" ]; then
  echo "==> 创建 .env（请编辑填写 DEEPSEEK_API_KEY）"
  sed "s#^DATA_DIR=.*#DATA_DIR=$APP_DIR/data#" "$APP_DIR/backend/.env.example" > "$APP_DIR/backend/.env"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 6. systemd 服务（通过 sed 输出到目标路径，不修改仓库文件）
echo "==> 安装 systemd 服务"
sed "s#/opt/yunhe#$APP_DIR#g" "$SCRIPT_DIR/backend.service" > /etc/systemd/system/yunhe-backend.service
systemctl daemon-reload
systemctl enable --now yunhe-backend
systemctl restart yunhe-backend

# 7. Nginx
echo "==> 配置 Nginx"
sed -e "s#/opt/yunhe#$APP_DIR#g" -e "s#127.0.0.1:8000#127.0.0.1:$BACKEND_PORT#g" \
  "$SCRIPT_DIR/nginx.conf" > /etc/nginx/conf.d/yunhe.conf
nginx -t
systemctl reload nginx || systemctl restart nginx

echo
echo "==> 安装完成！"
echo "    前端访问：  http://<服务器IP>/"
echo "    健康检查：  http://<服务器IP>/api/health"
echo "    编辑配置：  $APP_DIR/backend/.env（重点：DEEPSEEK_API_KEY）"
echo "    查看日志：  journalctl -u yunhe-backend -f"
