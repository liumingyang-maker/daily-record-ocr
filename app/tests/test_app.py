"""Tests for the FastAPI application."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "每日生产记录智能识别系统" in response.text
    assert "text/html" in response.headers["content-type"]
