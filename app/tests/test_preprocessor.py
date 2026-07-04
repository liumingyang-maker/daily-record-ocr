"""Tests for image preprocessor."""

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from app.infrastructure.image.preprocessor import (
    auto_rotate,
    enhance_contrast,
    load_image,
    preprocess_image,
    resize_to_standard,
)


@pytest.fixture
def portrait_img():
    return np.zeros((2500, 1800, 3), dtype=np.uint8)


@pytest.fixture
def landscape_img():
    return np.zeros((1800, 2500, 3), dtype=np.uint8)


def test_load_image_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_image(tmp_path / "missing.jpg")


def test_resize_to_standard(portrait_img):
    result = resize_to_standard(portrait_img, target=(900, 1250))
    assert result.shape == (1250, 900, 3)


def test_auto_rotate_landscape_to_portrait(landscape_img):
    result = auto_rotate(landscape_img)
    h, w = result.shape[:2]
    assert h > w


def test_auto_rotate_portrait_unchanged(portrait_img):
    result = auto_rotate(portrait_img)
    assert result.shape == portrait_img.shape


def test_enhance_contrast_preserves_shape(portrait_img):
    result = enhance_contrast(portrait_img)
    assert result.shape == portrait_img.shape


def test_preprocess_image_full_pipeline(tmp_path):
    src = tmp_path / "input.jpg"
    img = np.random.randint(0, 255, (1800, 2500, 3), dtype=np.uint8)
    cv2.imwrite(str(src), img)

    with patch("app.infrastructure.image.preprocessor.CORRECTED_IMAGES_DIR", tmp_path / "out"):
        result = preprocess_image(src, "job-001")

    assert result.exists()
    loaded = cv2.imread(str(result))
    assert loaded.shape == (2500, 1800, 3)
