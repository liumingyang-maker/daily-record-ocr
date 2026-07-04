@echo off
setlocal

echo ========================================
echo  构建 Windows 应用: DailyRecordOCR
echo ========================================

:: Navigate to project root
cd /d "%~dp0.."

set APP_NAME=DailyRecordOCR

:: Clean previous builds
if exist "dist\%APP_NAME%" rmdir /s /q "dist\%APP_NAME%"
if exist "build\%APP_NAME%" rmdir /s /q "build\%APP_NAME%"

:: Ensure virtual environment is active
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] 正在创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败，请确认已安装 Python 3.10+
        pause
        exit /b 1
    )
)
call .venv\Scripts\activate.bat

:: Install build dependencies
echo [INFO] 正在安装构建依赖...
pip install pyinstaller --quiet

:: Build with PyInstaller
echo [INFO] 正在打包...
pyinstaller ^
    --name "%APP_NAME%" ^
    --onedir ^
    --windowed ^
    --add-data "app/configs;app/configs" ^
    --add-data "app/interfaces/templates;app/interfaces/templates" ^
    --add-data "app/interfaces/static;app/interfaces/static" ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --collect-submodule uvicorn ^
    --noconfirm ^
    launcher\entry_point.py

if errorlevel 1 (
    echo [ERROR] 构建失败
    pause
    exit /b 1
)

echo.
echo [INFO] 构建完成: dist\%APP_NAME%\%APP_NAME%.exe
echo [INFO] 可将 dist\%APP_NAME% 文件夹打包分发
pause
