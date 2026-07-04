@echo off
setlocal

echo ========================================
echo  每日生产记录智能识别系统 - 安装依赖
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
echo [INFO] 正在安装依赖...
pip install -r requirements.txt

echo.
echo [INFO] 安装完成！运行 launcher\run.bat 启动程序。
pause
