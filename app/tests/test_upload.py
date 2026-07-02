"""Tests for image upload and job management."""

import io

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_image():
    fake_jpg = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    resp = client.post(
        "/api/jobs/upload",
        files={"file": ("test.jpg", fake_jpg, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert "job_no" in data
    assert data["status"] == "UPLOADED"


def test_list_jobs():
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_upload_unsupported_format():
    fake_txt = io.BytesIO(b"hello world")
    resp = client.post(
        "/api/jobs/upload",
        files={"file": ("test.txt", fake_txt, "text/plain")},
    )
    assert resp.status_code == 400


def test_jobs_page():
    resp = client.get("/jobs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "识别任务" in resp.text
