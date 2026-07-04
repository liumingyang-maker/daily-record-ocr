"""Tests for image cropper."""

import numpy as np
import pytest

from app.infrastructure.image.cropper import (
    crop_field_cells,
    crop_rect,
    crop_record_blocks,
    save_record_crops,
)


@pytest.fixture
def sample_image():
    return np.zeros((2500, 1800, 3), dtype=np.uint8)


@pytest.fixture
def template():
    return {
        "record_blocks": [
            {"id": "block_1", "rect": [50, 300, 1750, 800]},
            {"id": "block_2", "rect": [50, 850, 1750, 1350]},
            {"id": "block_3", "rect": [50, 1400, 1750, 1900]},
        ],
        "header_fields": [
            {"name": "time", "roi_in_record": [100, 10, 300, 60]},
            {"name": "customer_queue", "roi_in_record": [350, 10, 700, 60]},
        ],
        "machine_fields": [
            {"name": "搅拌机", "roi_in_record": [100, 420, 400, 470]},
        ],
        "temperature_fields": [
            {"name": "原料温度", "roi_in_record": [100, 120, 350, 170]},
        ],
    }


def test_crop_rect_returns_correct_shape():
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    result = crop_rect(img, [10, 20, 50, 80])
    assert result.shape == (60, 40, 3)


def test_crop_record_blocks_returns_three_blocks(sample_image, template):
    records = crop_record_blocks(sample_image, template, "job-001")
    assert len(records) == 3
    assert records[0]["image"].shape == (500, 1700, 3)
    assert records[1]["image"].shape == (500, 1700, 3)
    assert records[2]["image"].shape == (500, 1700, 3)


def test_crop_field_cells_saves_files(sample_image, template, tmp_path, monkeypatch):
    import app.infrastructure.image.cropper as cropper_mod

    monkeypatch.setattr(cropper_mod, "CELL_CROPS_DIR", tmp_path)

    record_img = np.zeros((500, 1700, 3), dtype=np.uint8)
    result = crop_field_cells(record_img, template, "job-002", 0)

    assert "time" in result
    assert "customer_queue" in result
    assert "搅拌机" in result
    assert "原料温度" in result
    assert (tmp_path / "job-002_r0_time.jpg").exists()
