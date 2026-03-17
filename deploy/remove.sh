#!/bin/bash
# =============================================================================
# fs-builder 卸载脚本
# 用法：sudo bash remove.sh [--keep-data]
# --keep-data  保留 /opt/fs-builder/output 和 .env，只删除程序和服务
# =============================================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

[[ $EUID -eq 0 ]] || error "请用 root 或 sudo 执行此脚本"

KEEP_DATA=false
[[ "$1" == "--keep-data" ]] && KEEP_DATA=true

APP_DIR="/opt/fs-builder"
SERVICE_NAME="fs-builder"
SERVICE_USER="fs-builder"
NGINX_CONF="/etc/nginx/sites-available/${SERVICE_NAME}"

echo ""
echo -e "${RED}╔══════════════════════════════════════╗${NC}"
echo -e "${RED}║       fs-builder 卸载                ║${NC}"
echo -e "${RED}╚══════════════════════════════════════╝${NC}"
echo ""

if [[ "$KEEP_DATA" == true ]]; then
  warning "--keep-data 模式：保留 output/ 和 .env"
else
  warning "将完全删除 $APP_DIR 目录下所有文件（包括生成的 .fs 文件）"
fi
echo ""

# 确认
read -r -p "确认卸载？[y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { info "已取消"; exit 0; }
echo ""

# ── 停止并删除 systemd 服务 ────────────────────────────────────────────────────
info "停止并删除 systemd 服务..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
  systemctl stop "$SERVICE_NAME"
fi
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
  systemctl disable "$SERVICE_NAME"
fi
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
success "systemd 服务已删除"

# ── 删除 nginx 配置 ────────────────────────────────────────────────────────────
info "删除 nginx 配置..."
rm -f "/etc/nginx/sites-enabled/${SERVICE_NAME}"
rm -f "$NGINX_CONF"
# 还原默认站点
if [[ -f /etc/nginx/sites-available/default ]]; then
  ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
fi
nginx -t && systemctl reload nginx
success "nginx 配置已删除"

# ── 删除 Let's Encrypt 证书（如有）──────────────────────────────────────────────
if command -v certbot &>/dev/null; then
  # 找出和此服务关联的域名证书
  CERT_DOMAINS=$(certbot certificates 2>/dev/null | grep -A2 "Path:.*${SERVICE_NAME}\|Path:.*/etc/letsencrypt" | grep "Domains:" | awk '{print $2}' || echo "")
  if [[ -n "$CERT_DOMAINS" ]]; then
    info "删除 SSL 证书（$CERT_DOMAINS）..."
    certbot delete --cert-name "$CERT_DOMAINS" --non-interactive 2>/dev/null || \
      warning "证书删除失败，可手动执行：sudo certbot delete"
    success "SSL 证书已删除"
  fi
fi

# ── 删除应用文件 ───────────────────────────────────────────────────────────────
info "删除应用文件..."
if [[ "$KEEP_DATA" == true ]] && [[ -d "$APP_DIR" ]]; then
  # 备份 output 和 .env
  TMP_BACKUP="/tmp/fs-builder-data-$(date +%Y%m%d%H%M%S)"
  mkdir -p "$TMP_BACKUP"
  [[ -d "$APP_DIR/output" ]] && cp -r "$APP_DIR/output" "$TMP_BACKUP/"
  [[ -f "$APP_DIR/.env"   ]] && cp    "$APP_DIR/.env"   "$TMP_BACKUP/"
  rm -rf "$APP_DIR"
  success "应用文件已删除"
  success "数据已备份到 $TMP_BACKUP"
else
  rm -rf "$APP_DIR"
  success "应用文件已删除"
fi

# ── 删除系统用户 ───────────────────────────────────────────────────────────────
info "删除系统用户 $SERVICE_USER..."
if id "$SERVICE_USER" &>/dev/null; then
  userdel "$SERVICE_USER"
  success "用户已删除"
else
  success "用户不存在，跳过"
fi

# ── 完成 ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}卸载完成。${NC}"
if [[ "$KEEP_DATA" == true ]]; then
  echo "  生成文件备份位置：$TMP_BACKUP"
fi
echo ""
