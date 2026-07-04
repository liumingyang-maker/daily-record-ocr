"""Crop images into record blocks and field cells using YAML template coordinates."""

from pathlib import Path

import cv2
import numpy as np
import yaml
from numpy import ndarray

from app.settings import CELL_CROPS_DIR, CONFIGS_DIR, RECORD_CROPS_DIR


def _load_template(template_name: str = "template_daily_record_v1") -> dict:
    path = CONFIGS_DIR / f"{template_name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["template"]


def crop_rect(img: ndarray, rect: list[int]) -> ndarray:
    """Crop image by [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = rect
    return img[y1:y2, x1:x2].copy()


def crop_record_blocks(
    image: ndarray, template: dict, job_id: str
) -> list[dict]:
    """Cut record areas from template config. Returns list of {index, image, rect}."""
    records = []
    for i, block in enumerate(template["record_blocks"]):
        cropped = crop_rect(image, block["rect"])
        records.append({"index": i, "image": cropped, "rect": block["rect"]})
    return records


def save_record_crops(records: list[dict], job_id: str) -> list[dict]:
    """Save cropped record images to RECORD_CROPS_DIR. Returns list with saved paths."""
    RECORD_CROPS_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for rec in records:
        filename = f"{job_id}_block_{rec['index']}.jpg"
        out_path = RECORD_CROPS_DIR / filename
        cv2.imwrite(str(out_path), rec["image"])
        saved.append({**rec, "path": str(out_path)})
    return saved


def crop_field_cells(
    record_image: ndarray,
    template: dict,
    job_id: str,
    record_index: int,
) -> dict[str, str]:
    """Cut field cells by ROI from a record block image. Returns {field_name: saved_path}."""
    CELL_CROPS_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}

    field_groups = ["header_fields", "machine_fields", "temperature_fields"]
    for group in field_groups:
        for field in template.get(group, []):
            name = field["name"]
            roi = field["roi_in_record"]
            cell = crop_rect(record_image, roi)
            filename = f"{job_id}_r{record_index}_{name}.jpg"
            out_path = CELL_CROPS_DIR / filename
            cv2.imwrite(str(out_path), cell)
            result[name] = str(out_path)

    return result
