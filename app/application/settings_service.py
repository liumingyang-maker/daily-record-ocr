"""Settings service — reads/writes .env file for runtime configuration."""

from pathlib import Path
from app.settings import BASE_DIR

ENV_PATH = BASE_DIR / ".env"

# Configurable settings with their defaults and metadata
SETTINGS_CONFIG = {
    "MIMO_API_KEY": {
        "label": "MiMo API Key",
        "description": "MiMo 视觉大模型的 API 密钥，用于记录级复核识别",
        "default": "",
        "type": "password",
        "group": "MiMo API",
    },
    "MIMO_MODEL": {
        "label": "MiMo 模型",
        "description": "使用的 MiMo 模型版本",
        "default": "mimo-v2.5",
        "type": "text",
        "group": "MiMo API",
    },
    "MIMO_BASE_URL": {
        "label": "MiMo API 地址",
        "description": "MiMo API 的基础 URL（留空使用默认地址）",
        "default": "",
        "type": "text",
        "group": "MiMo API",
    },
    "APP_HOST": {
        "label": "服务地址",
        "description": "Web 服务监听地址",
        "default": "127.0.0.1",
        "type": "text",
        "group": "应用设置",
    },
    "APP_PORT": {
        "label": "服务端口",
        "description": "Web 服务监听端口",
        "default": "8765",
        "type": "number",
        "group": "应用设置",
    },
    "LOG_LEVEL": {
        "label": "日志级别",
        "description": "日志输出级别（DEBUG/INFO/WARNING/ERROR）",
        "default": "INFO",
        "type": "select",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "group": "应用设置",
    },
}


def read_env() -> dict[str, str]:
    """Read current .env file into a dict."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def write_env(updates: dict[str, str]) -> None:
    """Update .env file with new values. Preserves comments and order."""
    existing = {}
    lines = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                key = key.strip()
                existing[key] = True
                if key in updates:
                    lines.append(f"{key}={updates[key]}")
                else:
                    lines.append(line)
            else:
                lines.append(line)

    # Add new keys that weren't in the file
    for key, value in updates.items():
        if key not in existing:
            lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_settings() -> dict:
    """Get current settings with metadata for the settings page."""
    env = read_env()
    groups = {}
    for key, config in SETTINGS_CONFIG.items():
        group = config["group"]
        if group not in groups:
            groups[group] = []
        groups[group].append({
            "key": key,
            "label": config["label"],
            "description": config["description"],
            "value": env.get(key, config["default"]),
            "default": config["default"],
            "type": config["type"],
            "options": config.get("options", []),
        })
    return groups


def save_settings(data: dict[str, str]) -> None:
    """Save settings to .env file."""
    # Only save keys that are in SETTINGS_CONFIG
    valid = {k: v for k, v in data.items() if k in SETTINGS_CONFIG}
    write_env(valid)
