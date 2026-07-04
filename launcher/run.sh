#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo " 每日生产记录智能识别系统 - 启动中..."
echo "========================================"

# Create virtual environment if missing
if [ ! -f ".venv/bin/python" ]; then
    echo "[INFO] 正在创建虚拟环境..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "[INFO] 正在检查依赖..."
pip install -r requirements.txt --quiet

# Create data directories
mkdir -p data/storage

# Open browser (macOS / Linux)
if command -v open &>/dev/null; then
    (sleep 2 && open "http://127.0.0.1:8765") &
elif command -v xdg-open &>/dev/null; then
    (sleep 2 && xdg-open "http://127.0.0.1:8765") &
fi

# Run the application
echo "[INFO] 启动服务 http://127.0.0.1:8765"
echo "[INFO] 按 Ctrl+C 停止服务"
python -m app.main
