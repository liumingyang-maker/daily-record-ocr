"""Tests for MiMo recognition API endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.interfaces.api_routes.mimo_service")
def test_mimo_recognize_job_success(mock_service):
    mock_service.recognize_job.return_value = {
        "job_id": 1,
        "processed_fields": 2,
        "results": [
            {
                "field_key": "time",
                "source": "mimo",
                "mimo_raw_text": "08:30",
                "mimo_confidence": 0.97,
            },
        ],
    }

    resp = client.post("/api/jobs/1/mimo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed_fields"] == 2
    assert data["results"][0]["mimo_raw_text"] == "08:30"
    mock_service.recognize_job.assert_called_once_with(1)


@patch("app.interfaces.api_routes.mimo_service")
def test_mimo_recognize_job_not_found(mock_service):
    mock_service.recognize_job.side_effect = ValueError("Job 999 not found")

    resp = client.post("/api/jobs/999/mimo")
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"]
