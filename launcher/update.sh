#!/usr/bin/env bash
# launcher/update.sh - 一键更新脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo " 每日生产记录智能识别系统 - 更新中..."
echo "========================================"

# Check if git repo
if [ ! -d ".git" ]; then
    echo "[ERROR] 当前目录不是 git 仓库，无法更新"
    exit 1
fi

# Show current version
echo "[INFO] 当前版本: $(git rev-parse --short HEAD) ($(git log -1 --format=%ci))"

# Fetch and check
echo "[INFO] 正在检查远程更新..."
git fetch origin 2>/dev/null || { echo "[ERROR] 无法连接远程仓库"; exit 1; }

# Check which branch to use
BRANCH=$(git branch --show-current)
REMOTE_BRANCH="origin/$BRANCH"

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "$REMOTE_BRANCH" 2>/dev/null || echo "")

if [ -z "$REMOTE" ]; then
    echo "[ERROR] 远程分支 $REMOTE_BRANCH 不存在"
    exit 1
fi

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[OK] 已是最新版本"
    exit 0
fi

BEHIND=$(git rev-list --count HEAD.."$REMOTE_BRANCH")
echo "[INFO] 发现 $BEHIND 个新版本:"
echo ""
git log --oneline HEAD.."$REMOTE_BRANCH" | head -20
echo ""

# Confirm
read -p "是否更新？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "[INFO] 已取消更新"
    exit 0
fi

# Pull
echo "[INFO] 正在拉取最新代码..."
git pull origin "$BRANCH"

# Install dependencies
echo "[INFO] 正在安装依赖..."
if [ -f ".venv/bin/pip" ]; then
    .venv/bin/pip install -r requirements.txt --quiet
elif [ -f ".venv/Scripts/pip" ]; then
    .venv/Scripts/pip install -r requirements.txt --quiet
else
    echo "[WARN] 未找到虚拟环境，请手动运行: pip install -r requirements.txt"
fi

echo ""
echo "[OK] 更新完成！"
echo "[INFO] 当前版本: $(git rev-parse --short HEAD) ($(git log -1 --format=%ci))"
echo "[INFO] 请重启服务: ./launcher/run.sh"
