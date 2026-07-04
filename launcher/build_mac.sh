#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="DailyRecordOCR"
DIST_DIR="dist"
BUILD_DIR="build"

echo "========================================"
echo " 构建 macOS 应用: $APP_NAME"
echo "========================================"

# Clean previous builds
rm -rf "$DIST_DIR/$APP_NAME" "$BUILD_DIR/$APP_NAME"

# Ensure virtual environment is active
if [ ! -f ".venv/bin/python" ]; then
    echo "[INFO] 正在创建虚拟环境..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install build dependencies
echo "[INFO] 正在安装构建依赖..."
pip install pyinstaller --quiet

# Build with PyInstaller
echo "[INFO] 正在打包..."
pyinstaller \
    --name "$APP_NAME" \
    --onedir \
    --windowed \
    --icon "launcher/icon.icns" \
    --add-data "app/configs:app/configs" \
    --add-data "app/interfaces/templates:app/interfaces/templates" \
    --add-data "app/interfaces/static:app/interfaces/static" \
    --hidden-import uvicorn \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.on \
    --collect-submodule uvicorn \
    --noconfirm \
    launcher/entry_point.py

# Copy Info.plist into .app bundle
if [ -f "launcher/Info.plist" ]; then
    PLIST_PATH="$DIST_DIR/$APP_NAME.app/Contents/Info.plist"
    if [ -f "$PLIST_PATH" ]; then
        cp launcher/Info.plist "$PLIST_PATH"
        echo "[INFO] 已更新 Info.plist"
    fi
fi

echo ""
echo "[INFO] 构建完成: $DIST_DIR/$APP_NAME.app"
echo "[INFO] 可直接双击运行，或拷贝到 Applications 文件夹"
