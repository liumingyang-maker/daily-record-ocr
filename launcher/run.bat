@echo off
setlocal

echo ========================================
echo  每日生产记录智能识别系统 - 启动中...
echo ========================================

:: Navigate to project root
cd /d "%~dp0.."

:: Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] 正在创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败，请确认已安装 Python 3.10+
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Install dependencies
echo [INFO] 正在检查依赖...
pip install -r requirements.txt --quiet

:: Create data directories
if not exist "data\storage" mkdir "data\storage"

:: Open browser after a short delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8765"

:: Run the application
echo [INFO] 启动服务 http://127.0.0.1:8765
echo [INFO] 按 Ctrl+C 停止服务
python -m app.main

pause
