"""Tests for preprocess_service — end-to-end preprocessing pipeline."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import ProductionRecord, RecognitionJob


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
        "app.application.preprocess_service.get_session", _mock_session
    )


@pytest.fixture()
def sample_job(db_session, tmp_path):
    """Create a RecognitionJob with a real source image."""
    src = tmp_path / "source.jpg"
    import cv2

    img = np.zeros((2500, 1800, 3), dtype=np.uint8)
    cv2.imwrite(str(src), img)

    job = RecognitionJob(
        job_no="JOB-TEST-001",
        source_image_path=str(src),
        status="UPLOADED",
    )
    db_session.add(job)
    db_session.flush()
    db_session.refresh(job)
    return job


@pytest.fixture()
def template():
    return {
        "record_blocks": [
            {"id": "block_1", "rect": [50, 300, 1750, 800]},
            {"id": "block_2", "rect": [50, 850, 1750, 1350]},
        ],
        "header_fields": [
            {"name": "time", "roi_in_record": [100, 10, 300, 60]},
        ],
        "machine_fields": [],
        "temperature_fields": [],
    }


@pytest.fixture()
def mock_infra(monkeypatch, tmp_path, template):
    """Mock heavy image operations to avoid real file I/O."""
    corrected_dir = tmp_path / "corrected"
    corrected_dir.mkdir()
    corrected_path = corrected_dir / "1.jpg"
    corrected_path.write_bytes(b"fake")

    monkeypatch.setattr(
        "app.application.preprocess_service.preprocess_image",
        lambda src, jid: corrected_path,
    )

    fake_img = np.zeros((2500, 1800, 3), dtype=np.uint8)
    monkeypatch.setattr(
        "app.application.preprocess_service.cv2.imread",
        lambda path: fake_img,
    )

    monkeypatch.setattr(
        "app.application.preprocess_service.load_config",
        lambda name: {"template": template},
    )

    records_with_path = [
        {"index": 0, "image": fake_img, "rect": [50, 300, 1750, 800], "path": str(tmp_path / "r0.jpg")},
        {"index": 1, "image": fake_img, "rect": [50, 850, 1750, 1350], "path": str(tmp_path / "r1.jpg")},
    ]
    monkeypatch.setattr(
        "app.application.preprocess_service.crop_record_blocks",
        lambda img, tpl, jid: [
            {"index": 0, "image": fake_img, "rect": [50, 300, 1750, 800]},
            {"index": 1, "image": fake_img, "rect": [50, 850, 1750, 1350]},
        ],
    )
    monkeypatch.setattr(
        "app.application.preprocess_service.save_record_crops",
        lambda recs, jid: records_with_path,
    )
    monkeypatch.setattr(
        "app.application.preprocess_service.crop_field_cells",
        lambda img, tpl, jid, idx: {"time": f"/tmp/fake_r{idx}_time.jpg"},
    )

    return corrected_path


def test_process_creates_corrected_image(sample_job, patch_session, mock_infra):
    from app.application.preprocess_service import process

    result = process(sample_job.id)

    assert result["corrected_path"] == str(mock_infra)
    assert Path(result["corrected_path"]).exists()


def test_process_creates_production_records(sample_job, patch_session, mock_infra, db_session):
    from app.application.preprocess_service import process

    result = process(sample_job.id)

    assert result["records_count"] == 2

    records = (
        db_session.query(ProductionRecord)
        .filter_by(job_id=sample_job.id)
        .order_by(ProductionRecord.record_index)
        .all()
    )
    assert len(records) == 2
    assert records[0].record_index == 0
    assert records[1].record_index == 1
    assert records[0].record_crop_path is not None


def test_process_updates_job_status(sample_job, patch_session, mock_infra, db_session):
    from app.application.preprocess_service import process

    result = process(sample_job.id)

    job = db_session.get(RecognitionJob, sample_job.id)
    assert job.status == "PREPROCESSED"
    assert job.corrected_image_path == result["corrected_path"]
