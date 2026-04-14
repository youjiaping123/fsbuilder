#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/fs-builder" ]]; then
  echo "错误：未找到可执行的 .venv/bin/fs-builder。" >&2
  echo "请先在项目根目录完成虚拟环境和依赖安装，例如：" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/pip install -e .[dev]" >&2
  exit 1
fi

echo "启动 Web UI：http://${HOST}:${PORT}"
echo "项目根目录：$ROOT_DIR"

exec ".venv/bin/fs-builder" serve --host "$HOST" --port "$PORT" "$@"
