"""Path and naming utilities for file storage."""

import hashlib
from datetime import datetime
from pathlib import Path

from app.settings import RAW_IMAGES_DIR


def generate_job_no() -> str:
    return "JOB" + datetime.now().strftime("%Y%m%d%H%M%S%f")


def get_raw_image_path(filename: str) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return RAW_IMAGES_DIR / today / filename


def calculate_file_hash(file_path: Path) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
