"""Configuration loading with small, explicit YAML files.

The lightweight application intentionally avoids a settings framework. Values are
loaded from ``config/app.yaml`` and may reference environment variables using
``${NAME}`` or ``${NAME:-default}`` syntax.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "app.yaml"
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _load_dotenv(path: Path) -> None:
    """Load a small .env file without adding another runtime dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv(PROJECT_ROOT / ".env")


def _expand_string(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        default = match.group(2) or ""
        return os.getenv(name, default)

    return _ENV_PATTERN.sub(replace, value)


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return _expand_string(value)
    if isinstance(value, list):
        return [_expand(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    return _expand(loaded)


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any]
    schema: dict[str, Any]
    export: dict[str, Any]
    project_root: Path = PROJECT_ROOT

    @property
    def app(self) -> dict[str, Any]:
        return self.raw.get("app", {})

    @property
    def preprocess(self) -> dict[str, Any]:
        return self.raw.get("preprocess", {})

    @property
    def vision(self) -> dict[str, Any]:
        return self.raw.get("vision", {})

    @property
    def jobs_dir(self) -> Path:
        return _resolve_path(self.app.get("jobs_dir", "data/jobs"))

    @property
    def host(self) -> str:
        return str(self.app.get("host", "127.0.0.1"))

    @property
    def port(self) -> int:
        return int(self.app.get("port", 8765))

    @property
    def max_upload_bytes(self) -> int:
        megabytes = float(self.app.get("max_upload_mb", 20))
        return int(megabytes * 1024 * 1024)

    def resolve_path(self, value: str | Path) -> Path:
        return _resolve_path(value)


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    raw = _read_yaml(DEFAULT_CONFIG_PATH)
    schema_path = _resolve_path(raw.get("schema_file", "config/record_schema.yaml"))
    export_path = _resolve_path(raw.get("export_file", "config/export.yaml"))
    return Settings(raw=raw, schema=_read_yaml(schema_path), export=_read_yaml(export_path))


def reload_settings() -> Settings:
    load_settings.cache_clear()
    return load_settings()
