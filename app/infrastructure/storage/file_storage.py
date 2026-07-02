"""File storage service for saving uploaded images."""

from pathlib import Path

from fastapi import UploadFile

from app.infrastructure.storage.path_manager import get_raw_image_path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


async def save_image(file: UploadFile) -> tuple[Path, str]:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext}")

    dest = get_raw_image_path(file.filename)
    dest.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    dest.write_bytes(content)

    return dest, file.filename
