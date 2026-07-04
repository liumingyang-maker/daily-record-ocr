"""Tests for export API endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.interfaces.api_routes.export_service")
def test_export_job_success(mock_service):
    mock_service.export_job.return_value = {
        "job_id": 1,
        "job_no": "JOB_001",
        "export_path": "/tmp/exports/JOB_001.xlsx",
    }

    resp = client.post("/api/jobs/1/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == 1
    assert data["job_no"] == "JOB_001"
    assert data["export_path"].endswith(".xlsx")
    mock_service.export_job.assert_called_once_with(1)
