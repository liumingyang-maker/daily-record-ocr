"""Tests for ocr_service — field-level OCR recognition pipeline."""

from contextlib import contextmanager
from unittest.mock import MagicMock

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    FieldRecognitionResult,
    ProductionRecord,
    RecognitionJob,
)
from app.infrastructure.ocr.engine import OCRResult


@pytest.fixture()
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture()
def patch_session(monkeypatch, db_session):
    """Patch get_session to use the test in-memory database."""

    @contextmanager
    def _mock_session():
        yield db_session
        db_session.commit()

    monkeypatch.setattr(
        "app.application.ocr_service.get_session", _mock_session
    )


@pytest.fixture()
def template():
    return {
        "header_fields": [{"name": "time", "roi_in_record": [100, 10, 300, 60]}],
        "machine_fields": [],
        "temperature_fields": [],
    }


@pytest.fixture()
def preprocessed_job(db_session, tmp_path):
    """Create a PREPROCESSED job with one ProductionRecord and a fake crop image."""
    crop_path = tmp_path / "r0.jpg"
    crop_path.write_bytes(b"fake_image_data")

    job = RecognitionJob(
        job_no="JOB-OCR-001",
        source_image_path="/tmp/source.jpg",
        status="PREPROCESSED",
    )
    db_session.add(job)
    db_session.flush()

    rec = ProductionRecord(
        job_id=job.id,
        record_index=0,
        record_crop_path=str(crop_path),
    )
    db_session.add(rec)
    db_session.flush()
    db_session.refresh(job)
    return job


@pytest.fixture()
def mock_infra(monkeypatch, tmp_path, template):
    """Mock image and OCR operations."""
    monkeypatch.setattr(
        "app.application.ocr_service.load_config",
        lambda name: {"template": template},
    )

    cell_path = str(tmp_path / "cell_time.jpg")
    monkeypatch.setattr(
        "app.application.ocr_service.crop_field_cells",
        lambda img, tpl, jid, idx: {"time": cell_path},
    )

    fake_img = np.zeros((100, 200, 3), dtype=np.uint8)
    monkeypatch.setattr(
        "app.application.ocr_service.cv2.imread",
        lambda path: fake_img,
    )

    mock_engine = MagicMock()
    mock_engine.recognize.return_value = OCRResult(text="08:30", confidence=0.98)
    monkeypatch.setattr(
        "app.application.ocr_service.get_ocr_engine",
        lambda: mock_engine,
    )
    return mock_engine


def test_recognize_job_returns_results(preprocessed_job, patch_session, mock_infra):
    from app.application.ocr_service import OcrService

    svc = OcrService()
    result = svc.recognize_job(preprocessed_job.id)

    assert result["job_id"] == preprocessed_job.id
    assert result["recognized_fields"] == 1
    assert result["results"][0]["field_key"] == "time"
    assert result["results"][0]["ocr_raw_text"] == "08:30"
    assert result["results"][0]["ocr_confidence"] == 0.98


def test_recognize_job_saves_field_results(
    preprocessed_job, patch_session, mock_infra, db_session
):
    from app.application.ocr_service import OcrService

    svc = OcrService()
    svc.recognize_job(preprocessed_job.id)

    results = (
        db_session.query(FieldRecognitionResult)
        .filter_by(job_id=preprocessed_job.id)
        .all()
    )
    assert len(results) == 1
    assert results[0].field_key == "time"
    assert results[0].source == "ocr"
    assert results[0].need_review is False


def test_recognize_job_rejects_wrong_status(db_session, patch_session, mock_infra):
    from app.application.ocr_service import OcrService

    job = RecognitionJob(job_no="JOB-BAD-001", status="UPLOADED")
    db_session.add(job)
    db_session.flush()

    svc = OcrService()
    with pytest.raises(ValueError, match="UPLOADED"):
        svc.recognize_job(job.id)
