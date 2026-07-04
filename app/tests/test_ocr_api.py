"""Tests for OCR recognition API endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.interfaces.api_routes.ocr_service")
def test_recognize_job_success(mock_service):
    mock_service.recognize_job.return_value = {
        "job_id": 1,
        "recognized_fields": 2,
        "results": [
            {"field_key": "time", "ocr_raw_text": "08:30", "ocr_confidence": 0.98, "need_review": False},
        ],
    }

    resp = client.post("/api/jobs/1/recognize")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recognized_fields"] == 2
    mock_service.recognize_job.assert_called_once_with(1)


@patch("app.interfaces.api_routes.ocr_service")
def test_recognize_job_bad_status(mock_service):
    mock_service.recognize_job.side_effect = ValueError(
        "Job 1 status is 'UPLOADED', expected 'PREPROCESSED'"
    )

    resp = client.post("/api/jobs/1/recognize")
    assert resp.status_code == 400
    assert "PREPROCESSED" in resp.json()["detail"]
