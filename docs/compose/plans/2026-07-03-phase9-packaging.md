# Phase 9: 打包部署 Implementation Plan

**Goal:** 创建启动脚本和打包配置，支持 Windows 和 macOS 两个平台。由于当前开发环境是 Linux，我们创建启动脚本和打包准备文件，用户在目标平台上执行实际打包。

## Global Constraints

- Windows 目标：one-folder + 启动器 bat
- macOS 版本：用户明确要求
- 使用 uvicorn 启动 FastAPI
- 所有依赖 freeze 到 requirements.txt

---

### Task 1: 启动脚本

**Covers:** [S2, S12]

**Files:**
- Create: `launcher/run.bat` (Windows 启动器)
- Create: `launcher/run.sh` (macOS/Linux 启动器)
- Create: `launcher/install.bat` (Windows 安装依赖)
- Create: `launcher/install.sh` (macOS/Linux 安装依赖)

- [ ] **Step 1: 创建启动脚本**

```bat
@echo off
REM launcher/run.bat - Windows 启动器
cd /d "%~dp0.."
if not exist ".venv" (
    echo [INFO] 首次运行，正在创建虚拟环境...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
echo [INFO] 启动每日生产记录智能识别系统...
start "" http://127.0.0.1:8765
python -m app.main
pause
```

```bash
#!/bin/bash
# launcher/run.sh - macOS/Linux 启动器
cd "$(dirname "$0")/.."
if [ ! -d ".venv" ]; then
    echo "[INFO] 首次运行，正在创建虚拟环境..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi
echo "[INFO] 启动每日生产记录智能识别系统..."
open http://127.0.0.1:8765 2>/dev/null || xdg-open http://127.0.0.1:8765 2>/dev/null &
python -m app.main
```

```bat
@echo off
REM launcher/install.bat - Windows 安装依赖
cd /d "%~dp0.."
if not exist ".venv" python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
echo [INFO] 依赖安装完成
pause
```

```bash
#!/bin/bash
# launcher/install.sh - macOS/Linux 安装依赖
cd "$(dirname "$0")/.."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
echo "[INFO] 依赖安装完成"
```

- [ ] **Step 2: 更新 requirements.txt**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
jinja2>=3.1.2
python-multipart>=0.0.6
sqlalchemy>=2.0.23
alembic>=1.13.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
loguru>=0.7.2
openpyxl>=3.1.2
httpx>=0.25.0
opencv-python-headless>=4.8.0
```

- [ ] **Step 3: 提交**

```bash
git add launcher/ requirements.txt
chmod +x launcher/run.sh launcher/install.sh
git commit -m "feat: launcher scripts for Windows and macOS"
```

---

### Task 2: macOS 打包配置

**Covers:** [S2]

**Files:**
- Create: `launcher/Info.plist` (macOS app 元数据)
- Create: `launcher/daily-record-ocr.icns` (macOS 图标占位)
- Create: `launcher/build_mac.sh` (macOS 打包脚本)
- Create: `launcher/build_windows.bat` (Windows 打包脚本)

- [ ] **Step 1: 创建打包脚本**

```bash
#!/bin/bash
# launcher/build_mac.sh - macOS 打包脚本
# 使用 pyinstaller 打包为 .app
cd "$(dirname "$0")/.."
source .venv/bin/activate

pip install pyinstaller

pyinstaller --name "每日生产记录识别系统" \
    --onedir \
    --windowed \
    --icon launcher/daily-record-ocr.icns \
    --add-data "app/configs:app/configs" \
    --add-data "app/interfaces/templates:app/interfaces/templates" \
    --add-data "app/interfaces/static:app/interfaces/static" \
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
    app/main.py

echo "[INFO] macOS 打包完成: dist/每日生产记录识别系统.app"
echo "[INFO] 可直接双击运行或拖到 Applications 文件夹"
```

```bat
@echo off
REM launcher/build_windows.bat - Windows 打包脚本
cd /d "%~dp0.."
call .venv\Scripts\activate.bat

pip install pyinstaller

pyinstaller --name "DailyRecordOCR" ^
    --onedir ^
    --noconsole ^
    --add-data "app/configs;app/configs" ^
    --add-data "app/interfaces/templates;app/interfaces/templates" ^
    --add-data "app/interfaces/static;app/interfaces/static" ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    app/main.py

echo [INFO] Windows 打包完成: dist\DailyRecordOCR\
echo [INFO] 可将 dist\DailyRecordOCR 文件夹复制到目标机器运行
pause
```

- [ ] **Step 2: 创建 macOS Info.plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>每日生产记录识别系统</string>
    <key>CFBundleDisplayName</key>
    <string>每日生产记录识别系统</string>
    <key>CFBundleIdentifier</key>
    <string>com.dailyrecord.ocr</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>main</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
```

- [ ] **Step 3: 提交**

```bash
git add launcher/
git commit -m "feat: build scripts for macOS and Windows with PyInstaller"
```
