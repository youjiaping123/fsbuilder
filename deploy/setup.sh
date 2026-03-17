#!/bin/bash
# =============================================================================
# fs-builder 首次部署脚本
# 适用于 Ubuntu 20.04 / 22.04 / 24.04
# 用法：bash setup.sh [--domain your.domain.com] [--port 8000]
# =============================================================================
set -e

# ── 颜色输出 ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── 参数解析 ──────────────────────────────────────────────────────────────────
DOMAIN=""
APP_PORT=8000
REPO_URL=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --domain) DOMAIN="$2"; shift 2 ;;
    --port)   APP_PORT="$2"; shift 2 ;;
    --repo)   REPO_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── 基本检查 ──────────────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || error "请用 root 或 sudo 执行此脚本"
command -v apt-get &>/dev/null || error "此脚本仅支持 Debian/Ubuntu 系统"

APP_DIR="/opt/fs-builder"
SERVICE_NAME="fs-builder"
SERVICE_USER="fs-builder"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       fs-builder 服务器部署           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""
info "应用目录：$APP_DIR"
info "服务端口：$APP_PORT"
[[ -n "$DOMAIN" ]] && info "绑定域名：$DOMAIN" || warning "未指定域名，将使用服务器 IP 访问"
echo ""

# ── Step 1: 系统依赖 ──────────────────────────────────────────────────────────
info "Step 1/6  安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx curl git

# Python 版本检查
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)
if [[ $PY_MAJOR -lt 3 || ($PY_MAJOR -eq 3 && $PY_MINOR -lt 9) ]]; then
  error "需要 Python 3.9+，当前版本 $PY_VER"
fi
success "Python $PY_VER ✓"

# ── Step 2: 创建系统用户 ──────────────────────────────────────────────────────
info "Step 2/6  创建服务用户..."
if ! id "$SERVICE_USER" &>/dev/null; then
  useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
  success "用户 $SERVICE_USER 已创建"
else
  success "用户 $SERVICE_USER 已存在，跳过"
fi

# ── Step 3: 部署代码 ──────────────────────────────────────────────────────────
info "Step 3/6  部署应用代码..."
if [[ -n "$REPO_URL" ]]; then
  if [[ -d "$APP_DIR/.git" ]]; then
    info "仓库已存在，执行 git pull..."
    git -C "$APP_DIR" pull
  else
    git clone "$REPO_URL" "$APP_DIR"
  fi
else
  # 无 git 仓库：将当前目录复制到 APP_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SRC_DIR="$(dirname "$SCRIPT_DIR")"
  if [[ "$SRC_DIR" != "$APP_DIR" ]]; then
    info "从 $SRC_DIR 复制文件..."
    mkdir -p "$APP_DIR"
    rsync -a --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
              --exclude='output/*.fs' --exclude='output/*_plan.json' \
              "$SRC_DIR/" "$APP_DIR/"
  fi
fi

# ── Step 4: Python 虚拟环境 & 依赖 ───────────────────────────────────────────
info "Step 4/6  安装 Python 依赖..."
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install . -q
success "依赖安装完成"

# ── Step 5: 配置文件 ──────────────────────────────────────────────────────────
info "Step 5/6  配置环境变量..."
if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo ""
  warning "已创建 .env 文件，请填写 API Key："
  warning "  nano $APP_DIR/.env"
  echo ""
fi

# 确保 output 目录存在
mkdir -p "$APP_DIR/output"

# 权限设置
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
chmod 750 "$APP_DIR"
chmod 640 "$APP_DIR/.env"
success "权限设置完成"

# ── Step 6a: systemd 服务 ─────────────────────────────────────────────────────
info "Step 6/6  配置 systemd 服务..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=fs-builder — Natural Language to FeatureScript
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/.venv/bin/python3 app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=${APP_DIR}/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
  success "服务已启动 ✓"
else
  error "服务启动失败，查看日志：journalctl -u $SERVICE_NAME -n 30"
fi

# ── Step 6b: nginx 配置 ───────────────────────────────────────────────────────
info "Step 6/6  配置 nginx..."

NGINX_CONF="/etc/nginx/sites-available/${SERVICE_NAME}"
SERVER_NAME="${DOMAIN:-_}"

cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name ${SERVER_NAME};

    # 安全头
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass         http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;

        # SSE 流式输出必须关闭缓冲
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   Connection        '';
        chunked_transfer_encoding on;
    }
}
EOF

# 启用站点
ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/${SERVICE_NAME}"
# 移除默认站点（如果存在）
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
success "nginx 配置完成 ✓"

# ── 完成 ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           部署完成！                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
if [[ -n "$DOMAIN" ]]; then
  echo -e "  访问地址：${GREEN}http://${DOMAIN}${NC}"
else
  echo -e "  访问地址：${GREEN}http://${SERVER_IP}${NC}"
fi

echo ""
echo "  常用命令："
echo "    查看日志：  sudo journalctl -u fs-builder -f"
echo "    重启服务：  sudo systemctl restart fs-builder"
echo "    停止服务：  sudo systemctl stop fs-builder"
echo "    更新代码：  sudo bash $APP_DIR/deploy/update.sh"
echo ""

if [[ ! -s "$APP_DIR/.env" ]] || grep -q "sk-\.\.\." "$APP_DIR/.env" 2>/dev/null; then
  echo -e "${YELLOW}⚠  别忘了填写 .env 文件中的 API Key！${NC}"
  echo "    sudo nano $APP_DIR/.env"
  echo "    sudo systemctl restart fs-builder"
  echo ""
fi
