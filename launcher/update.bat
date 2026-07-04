@echo off
REM launcher/update.bat - 一键更新脚本 (Windows)
cd /d "%~dp0.."

echo ========================================
echo  每日生产记录智能识别系统 - 更新中...
echo ========================================

REM Check if git repo
if not exist ".git" (
    echo [ERROR] 当前目录不是 git 仓库，无法更新
    pause
    exit /b 1
)

REM Show current version
for /f "tokens=*" %%i in ('git rev-parse --short HEAD') do set LOCAL_HASH=%%i
for /f "tokens=*" %%i in ('git log -1 --format%%ci') do set LOCAL_DATE=%%i
echo [INFO] 当前版本: %LOCAL_HASH% (%LOCAL_DATE%)

REM Fetch
echo [INFO] 正在检查远程更新...
git fetch origin
if errorlevel 1 (
    echo [ERROR] 无法连接远程仓库
    pause
    exit /b 1
)

REM Get branch
for /f "tokens=*" %%i in ('git branch --show-current') do set BRANCH=%%i

REM Check behind
for /f "tokens=*" %%i in ('git rev-list --count HEAD..origin/%BRANCH%') do set BEHIND=%%i
if "%BEHIND%"=="0" (
    echo [OK] 已是最新版本
    pause
    exit /b 0
)

echo [INFO] 发现 %BEHIND% 个新版本:
echo.
git log --oneline HEAD..origin/%BRANCH%
echo.

REM Confirm
set /p CONFIRM="是否更新？(y/N): "
if /i not "%CONFIRM%"=="y" (
    echo [INFO] 已取消更新
    pause
    exit /b 0
)

REM Pull
echo [INFO] 正在拉取最新代码...
git pull origin %BRANCH%

REM Install dependencies
echo [INFO] 正在安装依赖...
if exist ".venv\Scripts\pip.exe" (
    .venv\Scripts\pip install -r requirements.txt --quiet
) else (
    echo [WARN] 未找到虚拟环境，请手动运行: pip install -r requirements.txt
)

echo.
echo [OK] 更新完成！
for /f "tokens=*" %%i in ('git rev-parse --short HEAD') do set NEW_HASH=%%i
for /f "tokens=*" %%i in ('git log -1 --format%%ci') do set NEW_DATE=%%i
echo [INFO] 当前版本: %NEW_HASH% (%NEW_DATE%)
echo [INFO] 请重启服务: launcher\run.bat
pause
