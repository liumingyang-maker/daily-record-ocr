"""File-backed job storage.

For a single-user desktop tool, one JSON file per job is simpler than a database,
portable, and easy to inspect or repair by hand.
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from lite_app.config import load_settings

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _safe_filename(filename: str, fallback: str) -> str:
    cleaned = _SAFE_NAME.sub("_", Path(filename or fallback).name).strip("._")
    return cleaned or fallback


def create_job(files: Iterable[tuple[str, bytes]], rotation: str = "auto") -> dict[str, Any]:
    settings = load_settings()
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    directory = settings.jobs_dir / job_id
    directory.mkdir(parents=True, exist_ok=False)

    images: list[dict[str, Any]] = []
    for index, (original_name, content) in enumerate(files, start=1):
        safe_name = _safe_filename(original_name, f"image_{index}.jpg")
        source_name = f"source_{index:02d}_{safe_name}"
        (directory / source_name).write_bytes(content)
        images.append(
            {
                "original_name": original_name or safe_name,
                "source": source_name,
                "prepared": None,
                "size_bytes": len(content),
            }
        )

    timestamp = _now()
    job = {
        "id": job_id,
        "status": "UPLOADED",
        "created_at": timestamp,
        "updated_at": timestamp,
        "rotation": rotation,
        "images": images,
        "provider": "",
        "model": "",
        "validation_errors": [],
        "error": "",
        "export_file": None,
    }
    save_job(job)
    return job


def job_dir(job_id: str) -> Path:
    directory = load_settings().jobs_dir / job_id
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Job not found: {job_id}")
    return directory


def load_job(job_id: str) -> dict[str, Any]:
    path = job_dir(job_id) / "job.json"
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid job metadata: {path}")
    return payload


def save_job(job: dict[str, Any]) -> None:
    job = dict(job)
    job["updated_at"] = _now()
    directory = load_settings().jobs_dir / str(job["id"])
    _atomic_write_json(directory / "job.json", job)


def update_job(job_id: str, **changes: Any) -> dict[str, Any]:
    job = load_job(job_id)
    job.update(changes)
    save_job(job)
    return job


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    root = load_settings().jobs_dir
    if not root.exists():
        return []
    jobs: list[dict[str, Any]] = []
    for metadata in root.glob("*/job.json"):
        try:
            with metadata.open("r", encoding="utf-8") as handle:
                job = json.load(handle)
            if isinstance(job, dict):
                jobs.append(job)
        except (OSError, json.JSONDecodeError):
            continue
    jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return jobs[:limit]


def save_result(job_id: str, result: dict[str, Any]) -> Path:
    path = job_dir(job_id) / "result.json"
    _atomic_write_json(path, result)
    return path


def load_result(job_id: str) -> dict[str, Any] | None:
    path = job_dir(job_id) / "result.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Result must be a JSON object: {path}")
    return payload
