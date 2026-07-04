"""Tests for preprocess API endpoint."""

import io
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _upload_image() -> int:
    """Upload an image and return the job_id."""
    fake_jpg = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    resp = client.post(
        "/api/jobs/upload",
        files={"file": ("test.jpg", fake_jpg, "image/jpeg")},
    )
    assert resp.status_code == 200
    return resp.json()["job_id"]


@patch("app.interfaces.api_routes.process")
def test_preprocess_job(mock_process):
    job_id = _upload_image()
    mock_process.return_value = {
        "job_id": job_id,
        "corrected_path": "/tmp/fake_corrected.jpg",
        "records_count": 3,
        "field_crops": [],
    }

    resp = client.post(f"/api/jobs/{job_id}/preprocess")
    assert resp.status_code == 200
    data = resp.json()
    assert data["records_count"] == 3
    mock_process.assert_called_once_with(job_id)


@patch("app.interfaces.api_routes.process")
def test_preprocess_not_found(mock_process):
    mock_process.side_effect = ValueError("Job 99999 not found")

    resp = client.post("/api/jobs/99999/preprocess")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
