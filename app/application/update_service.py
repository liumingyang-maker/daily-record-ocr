"""Update service — check for updates and pull latest from GitHub."""

import subprocess
import sys
from pathlib import Path
from app.settings import BASE_DIR


def run_git(args: list[str]) -> tuple[int, str]:
    """Run a git command and return (returncode, output)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 1, str(e)


def get_local_info() -> dict:
    """Get local git info: commit hash, date, branch."""
    _, hash_short = run_git(["rev-parse", "--short", "HEAD"])
    _, hash_full = run_git(["rev-parse", "HEAD"])
    _, date = run_git(["log", "-1", "--format=%ci"])
    _, branch = run_git(["branch", "--show-current"])
    _, commit_count = run_git(["rev-list", "--count", "HEAD"])
    return {
        "hash": hash_short,
        "hash_full": hash_full,
        "date": date[:19] if date else "",
        "branch": branch,
        "commit_count": commit_count,
    }


def get_remote_info() -> dict:
    """Fetch remote and get latest commit info."""
    # Fetch first
    code, msg = run_git(["fetch", "origin"])
    if code != 0:
        return {"error": f"无法连接远程仓库: {msg}"}

    _, hash_short = run_git(["rev-parse", "--short", "origin/main"])
    if not hash_short:
        _, hash_short = run_git(["rev-parse", "--short", "origin/master"])
    _, date = run_git(["log", "-1", "--format=%ci", "origin/main"])
    if not date:
        _, date = run_git(["log", "-1", "--format=%ci", "origin/master"])
    return {
        "hash": hash_short,
        "date": date[:19] if date else "",
    }


def check_update() -> dict:
    """Check if there are updates available."""
    local = get_local_info()
    remote = get_remote_info()

    if "error" in remote:
        return {
            "status": "error",
            "message": remote["error"],
            "local": local,
        }

    # Compare commits
    _, behind = run_git(["rev-list", "--count", "HEAD..origin/main"])
    if not behind or behind == "0":
        _, behind = run_git(["rev-list", "--count", "HEAD..origin/master"])

    if not behind or behind == "0":
        return {
            "status": "up_to_date",
            "message": "已是最新版本",
            "local": local,
            "remote": remote,
        }

    # Get new commits log
    _, log = run_git(["log", "--oneline", f"HEAD..origin/main"])
    if not log:
        _, log = run_git(["log", "--oneline", f"HEAD..origin/master"])

    new_commits = []
    for line in log.splitlines():
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                new_commits.append({"hash": parts[0], "message": parts[1]})

    return {
        "status": "update_available",
        "message": f"有 {behind} 个新版本可用",
        "behind": int(behind),
        "local": local,
        "remote": remote,
        "new_commits": new_commits[:10],
    }


def do_update() -> dict:
    """Pull latest changes and install dependencies."""
    # Stash any local changes
    run_git(["stash"])

    # Pull
    code, msg = run_git(["pull", "origin", "main"])
    if code != 0:
        code, msg = run_git(["pull", "origin", "master"])
    if code != 0:
        return {
            "status": "error",
            "message": f"拉取更新失败: {msg}",
        }

    # Install dependencies
    pip = str(BASE_DIR / ".venv" / "bin" / "pip")
    if sys.platform == "win32":
        pip = str(BASE_DIR / ".venv" / "Scripts" / "pip")

    try:
        result = subprocess.run(
            [pip, "install", "-r", str(BASE_DIR / "requirements.txt"), "--quiet"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return {
                "status": "partial",
                "message": f"代码已更新，但依赖安装失败: {result.stderr[:200]}",
            }
    except FileNotFoundError:
        return {
            "status": "partial",
            "message": "代码已更新，请手动运行 pip install -r requirements.txt",
        }

    local = get_local_info()
    return {
        "status": "success",
        "message": "更新成功！请重启服务以使用新版本。",
        "local": local,
    }
