"""Image preprocessing: rotate, resize, enhance contrast, full pipeline."""

from pathlib import Path

import cv2
import numpy as np
from numpy import ndarray

from app.settings import CORRECTED_IMAGES_DIR


def load_image(path: str | Path) -> ndarray:
    """Load an image from disk as a BGR ndarray."""
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {path}")
    return img


def resize_to_standard(img: ndarray, target: tuple[int, int] = (1800, 2500)) -> ndarray:
    """Resize image to target (width, height)."""
    w, h = target
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def auto_rotate(img: ndarray) -> ndarray:
    """Rotate a landscape image to portrait orientation."""
    h, w = img.shape[:2]
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    return img


def enhance_contrast(img: ndarray) -> ndarray:
    """Apply CLAHE contrast enhancement on the L channel in LAB color space."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def preprocess_image(image_path: str | Path, job_id: str) -> Path:
    """Full preprocessing pipeline. Returns path to saved corrected image."""
    img = load_image(image_path)
    img = auto_rotate(img)
    img = enhance_contrast(img)
    img = resize_to_standard(img)

    CORRECTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CORRECTED_IMAGES_DIR / f"{job_id}.jpg"
    cv2.imwrite(str(out_path), img)
    return out_path
