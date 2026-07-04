#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo " 每日生产记录智能识别系统 - 安装依赖"
echo "========================================"

# Create virtual environment if missing
if [ ! -f ".venv/bin/python" ]; then
    echo "[INFO] 正在创建虚拟环境..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "[INFO] 正在安装依赖..."
pip install -r requirements.txt

echo ""
echo "[INFO] 安装完成！运行 ./launcher/run.sh 启动程序。"
