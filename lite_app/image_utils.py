"""Small Pillow-based image preparation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

_ROTATIONS = {
    "none": 0,
    "cw90": -90,
    "ccw90": 90,
    "180": 180,
}


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        background.alpha_composite(rgba)
        return background.convert("RGB")
    return image.convert("RGB")


def prepare_image(
    source: Path,
    destination: Path,
    preprocess_config: dict[str, Any],
    rotation: str = "auto",
) -> Path:
    """Normalize EXIF, optionally rotate, resize, and save as JPEG."""

    max_side = int(preprocess_config.get("max_side", 2048))
    quality = int(preprocess_config.get("jpeg_quality", 90))
    auto_landscape = bool(preprocess_config.get("auto_rotate_portrait_to_landscape", True))
    auto_direction = str(preprocess_config.get("auto_landscape_direction", "ccw90"))

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        image.load()

    if rotation in _ROTATIONS:
        degrees = _ROTATIONS[rotation]
        if degrees:
            image = image.rotate(degrees, expand=True)
    elif rotation == "auto" and auto_landscape and image.height > image.width:
        degrees = _ROTATIONS.get(auto_direction, 90)
        image = image.rotate(degrees, expand=True)

    image = _flatten_to_rgb(image)
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="JPEG", quality=quality, optimize=True)
    return destination
