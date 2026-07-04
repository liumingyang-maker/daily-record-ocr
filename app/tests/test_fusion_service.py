"""Tests for fusion_service — candidate fusion pipeline."""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    FieldCandidate,
    FieldRecognitionResult,
    Material,
    ProductionRecord,
    RecognitionJob,
)


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
        "app.application.fusion_service.get_session", _mock_session
    )


@pytest.fixture()
def rules_config():
    return {
        "field_rules": {
            "material_name": {"type": "string", "required": True},
        },
        "confidence_thresholds": {"green": 0.95, "yellow": 0.80, "red": 0.0},
    }


@pytest.fixture()
def mock_config(monkeypatch, rules_config):
    monkeypatch.setattr(
        "app.application.fusion_service.load_config",
        lambda name: rules_config if name == "rules" else {},
    )


@pytest.fixture()
def job_with_fields(db_session):
    job = RecognitionJob(job_no="JOB-FUSE-001", status="RECOGNIZED")
    db_session.add(job)
    db_session.flush()

    rec = ProductionRecord(job_id=job.id, record_index=0)
    db_session.add(rec)
    db_session.flush()

    # A field with both OCR and MiMo results
    fr = FieldRecognitionResult(
        job_id=job.id,
        record_id=rec.id,
        field_key="time",
        ocr_raw_text="08:00",
        ocr_confidence=0.85,
        mimo_raw_text="08:30",
        mimo_confidence=0.97,
    )
    db_session.add(fr)
    db_session.flush()

    # A material_name field with a known material in DB
    mat = Material(standard_name="PE-LLD 7042", material_code="M001", status="ACTIVE")
    db_session.add(mat)
    db_session.flush()

    fr_mat = FieldRecognitionResult(
        job_id=job.id,
        record_id=rec.id,
        field_key="material_name",
        ocr_raw_text="PE-LLD 7042",
        ocr_confidence=0.90,
    )
    db_session.add(fr_mat)
    db_session.flush()

    db_session.refresh(job)
    return job


def test_fuse_writes_candidates_and_picks_best(
    job_with_fields, patch_session, mock_config, db_session
):
    from app.application.fusion_service import FusionService

    svc = FusionService()
    result = svc.fuse_job(job_with_fields.id)

    assert result["job_id"] == job_with_fields.id
    assert result["fused_fields"] == 2

    # time field: MiMo should win (0.97 > 0.85)
    time_field = (
        db_session.query(FieldRecognitionResult)
        .filter_by(job_id=job_with_fields.id, field_key="time")
        .first()
    )
    assert time_field.final_value == "08:30"
    assert time_field.final_confidence == 0.97
    assert time_field.source == "mimo"

    time_candidates = (
        db_session.query(FieldCandidate)
        .filter_by(field_result_id=time_field.id)
        .order_by(FieldCandidate.rank)
        .all()
    )
    assert len(time_candidates) == 2
    assert time_candidates[0].rank == 1
    assert time_candidates[0].source == "mimo"


def test_fuse_material_field_includes_dict_candidates(
    job_with_fields, patch_session, mock_config, db_session
):
    from app.application.fusion_service import FusionService

    svc = FusionService()
    svc.fuse_job(job_with_fields.id)

    mat_field = (
        db_session.query(FieldRecognitionResult)
        .filter_by(job_id=job_with_fields.id, field_key="material_name")
        .first()
    )
    candidates = (
        db_session.query(FieldCandidate)
        .filter_by(field_result_id=mat_field.id)
        .all()
    )
    sources = {c.source for c in candidates}
    # Should have at least ocr + dict_exact
    assert "ocr" in sources
    assert "dict_exact" in sources
