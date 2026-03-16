#!/bin/bash
cd "$(dirname "$0")"

# 优先使用 venv 内的 Python（依赖已安装在这里）
if [ -f ".venv/bin/python3" ]; then
  PYTHON=".venv/bin/python3"
elif command -v python3 &>/dev/null; then
  PYTHON="python3"
else
  echo "Error: python3 not found."
  exit 1
fi

# 启动服务器并自动打开浏览器
echo "Starting fs-builder at http://localhost:8000 ..."
$PYTHON app.py &
SERVER_PID=$!

sleep 1.5
open "http://localhost:8000"   # macOS

wait $SERVER_PID
