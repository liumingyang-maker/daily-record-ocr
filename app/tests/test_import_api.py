"""Tests for import API endpoints."""

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)


def _make_xlsx_bytes():
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "批号", "物料", "用量"])
    ws.append(["2025-01-01", "客户A", "产品X", "B001", "物料1", 10.5])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_upload_file():
    xlsx = _make_xlsx_bytes()
    resp = client.post(
        "/api/import/upload",
        files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"profile": "type_a_flat"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_no"].startswith("IMP")
    assert data["status"] == "PARSED"
    assert data["total_rows"] == 1
    assert data["import_profile"] == "type_a_flat"


def test_upload_unsupported_format():
    fake = io.BytesIO(b"hello world")
    resp = client.post(
        "/api/import/upload",
        files={"file": ("test.txt", fake, "text/plain")},
        data={"profile": "type_a_flat"},
    )
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


def test_list_batches():
    resp = client.get("/api/import/batches")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_get_batch_not_found():
    resp = client.get("/api/import/batches/99999")
    assert resp.status_code == 404
