"""Tests for review API endpoints (field update and job confirm)."""

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import (
    RecognitionJob,
    ProductionRecord,
    FieldRecognitionResult,
    ManualCorrectionLog,
)

client = TestClient(app)


def _create_test_job_with_fields():
    """Create a test job with a record and field for testing."""
    job_no = f"TEST-REVIEW-{uuid.uuid4().hex[:8]}"
    with get_session() as session:
        job = RecognitionJob(job_no=job_no, status="NEED_REVIEW")
        session.add(job)
        session.flush()

        record = ProductionRecord(
            job_id=job.id,
            record_index=1,
            time_value="08:30",
        )
        session.add(record)
        session.flush()

        field = FieldRecognitionResult(
            job_id=job.id,
            record_id=record.id,
            field_key="customer_name",
            field_label="客户名称",
            final_value="客户A",
            final_confidence=0.85,
            ocr_raw_text="客户A",
            ocr_confidence=0.90,
            manual_corrected=False,
        )
        session.add(field)
        session.flush()

        return job.id, field.id


def test_patch_field_updates_value():
    """PATCH /api/fields/{field_id} should update final_value and create correction log."""
    job_id, field_id = _create_test_job_with_fields()

    resp = client.patch(
        f"/api/fields/{field_id}",
        json={"final_value": "客户B"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_id"] == field_id
    assert data["final_value"] == "客户B"
    assert data["manual_corrected"] is True
    assert "log_id" in data

    with get_session() as session:
        field = session.get(FieldRecognitionResult, field_id)
        assert field.final_value == "客户B"
        assert field.manual_corrected is True

        log = session.query(ManualCorrectionLog).filter_by(field_key="customer_name").first()
        assert log is not None
        assert log.old_value == "客户A"
        assert log.new_value == "客户B"


def test_confirm_job_sets_status():
    """POST /api/jobs/{job_id}/confirm should set job status to CONFIRMED."""
    job_id, _ = _create_test_job_with_fields()

    resp = client.post(f"/api/jobs/{job_id}/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "CONFIRMED"

    with get_session() as session:
        job = session.get(RecognitionJob, job_id)
        assert job.status == "CONFIRMED"
