"""Tests for fusion API endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.interfaces.api_routes.fusion_service")
def test_fuse_job_success(mock_service):
    mock_service.fuse_job.return_value = {
        "job_id": 1,
        "fused_fields": 5,
    }

    resp = client.post("/api/jobs/1/fuse")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == 1
    assert data["fused_fields"] == 5
    mock_service.fuse_job.assert_called_once_with(1)
