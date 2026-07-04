"""Tests for mimo_service — MiMo vision recognition pipeline."""

from contextlib import contextmanager
from unittest.mock import MagicMock

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    FieldRecognitionResult,
    MimoCache,
    MimoRequestLog,
    ProductionRecord,
    RecognitionJob,
)
from app.infrastructure.vision.mimo_client import MimoResult


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
    @contextmanager
    def _mock_session():
        yield db_session
        db_session.commit()

    monkeypatch.setattr(
        "app.application.mimo_service.get_session", _mock_session
    )


@pytest.fixture()
def template():
    return {
        "header_fields": [{"name": "time", "roi_in_record": [100, 10, 300, 60]}],
        "machine_fields": [],
        "temperature_fields": [],
    }


@pytest.fixture()
def mimo_config():
    return {
        "enabled": True,
        "mode": "record_level",
        "model": "mimo-v2.5",
        "prompt_version": "daily_record_v1_202607",
        "cache_enabled": True,
    }


@pytest.fixture()
def preprocessed_job(db_session, tmp_path):
    crop_path = tmp_path / "r0.jpg"
    crop_path.write_bytes(b"fake_image_data")

    job = RecognitionJob(
        job_no="JOB-MIMO-001",
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

    field = FieldRecognitionResult(
        job_id=job.id,
        record_id=rec.id,
        field_key="time",
        cell_crop_path="/tmp/cell_time.jpg",
        ocr_raw_text="08:00",
        ocr_confidence=0.85,
        source="ocr",
    )
    db_session.add(field)
    db_session.flush()
    db_session.refresh(job)
    return job


@pytest.fixture()
def mock_infra(monkeypatch, tmp_path, template, mimo_config):
    monkeypatch.setattr(
        "app.application.mimo_service.load_config",
        lambda name: {"template": template} if name == "template_daily_record_v1" else {"mimo": mimo_config},
    )

    cell_path = str(tmp_path / "cell_time.jpg")
    tmp_path.joinpath("cell_time.jpg").write_bytes(b"fake_cell_data")
    monkeypatch.setattr(
        "app.application.mimo_service.crop_field_cells",
        lambda img, tpl, jid, idx: {"time": cell_path},
    )

    fake_img = np.zeros((100, 200, 3), dtype=np.uint8)
    monkeypatch.setattr(
        "app.application.mimo_service.cv2.imread",
        lambda path: fake_img,
    )

    mock_client = MagicMock()
    mock_client.recognize_record.return_value = MimoResult(
        fields={
            "time": {
                "value": "08:30",
                "confidence": 0.97,
                "raw_text": "08:30",
            }
        },
        raw_response='{"time": "08:30"}',
        success=True,
    )
    monkeypatch.setattr(
        "app.application.mimo_service.get_mimo_client",
        lambda: mock_client,
    )
    return mock_client


def test_recognize_job_returns_results(preprocessed_job, patch_session, mock_infra):
    from app.application.mimo_service import MimoService

    svc = MimoService()
    result = svc.recognize_job(preprocessed_job.id)

    assert result["job_id"] == preprocessed_job.id
    assert result["processed_fields"] == 1
    assert result["results"][0]["field_key"] == "time"
    assert result["results"][0]["mimo_raw_text"] == "08:30"
    assert result["results"][0]["mimo_confidence"] == 0.97


def test_recognize_job_updates_field_and_sets_mimo_used(
    preprocessed_job, patch_session, mock_infra, db_session
):
    from app.application.mimo_service import MimoService

    svc = MimoService()
    svc.recognize_job(preprocessed_job.id)

    field = (
        db_session.query(FieldRecognitionResult)
        .filter_by(job_id=preprocessed_job.id, field_key="time")
        .first()
    )
    assert field.mimo_raw_text == "08:30"
    assert field.mimo_confidence == 0.97

    db_session.refresh(preprocessed_job)
    assert preprocessed_job.mimo_used is True


def test_recognize_job_logs_and_caches(
    preprocessed_job, patch_session, mock_infra, db_session
):
    from app.application.mimo_service import MimoService

    svc = MimoService()
    svc.recognize_job(preprocessed_job.id)

    logs = db_session.query(MimoRequestLog).filter_by(job_id=preprocessed_job.id).all()
    assert len(logs) == 1
    assert logs[0].success is True
    assert logs[0].model == "mimo-v2.5"

    caches = db_session.query(MimoCache).all()
    assert len(caches) == 1
    assert caches[0].prompt_version == "daily_record_v1_202607"
