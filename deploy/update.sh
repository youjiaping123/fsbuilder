#!/bin/bash
# =============================================================================
# fs-builder 代码更新脚本
# 用法：sudo bash update.sh
# =============================================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

APP_DIR="/opt/fs-builder"
SERVICE_NAME="fs-builder"

[[ -d "$APP_DIR" ]] || error "应用目录 $APP_DIR 不存在，请先执行 setup.sh"

info "更新 fs-builder..."

# git 仓库：pull 最新代码
if [[ -d "$APP_DIR/.git" ]]; then
  info "拉取最新代码（git pull）..."
  git -C "$APP_DIR" pull origin main
else
  # 非 git：将调用方目录同步过来
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SRC_DIR="$(dirname "$SCRIPT_DIR")"
  info "同步文件从 $SRC_DIR ..."
  rsync -a --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
            --exclude='output/*.fs' --exclude='output/*_plan.json' \
            --exclude='.env' \
            "$SRC_DIR/" "$APP_DIR/"
fi

# 更新依赖
info "更新 Python 依赖..."
"$APP_DIR/.venv/bin/pip" install . -q
success "依赖已更新"

# 修复权限
chown -R fs-builder:fs-builder "$APP_DIR"

# 重启服务
info "重启服务..."
systemctl restart "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
  success "服务已重启 ✓"
  echo ""
  echo "  查看日志：sudo journalctl -u $SERVICE_NAME -f"
else
  error "服务重启失败，查看日志：journalctl -u $SERVICE_NAME -n 30"
fi
