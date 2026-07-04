"""Tests for confirm import API endpoint and import detail page."""

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
    ws.append(["2025-01-01", "客户A", "产品X", "B001", "物料2", 5.0])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _upload_batch():
    """Helper: upload a file and return batch_id."""
    xlsx = _make_xlsx_bytes()
    resp = client.post(
        "/api/import/upload",
        files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"profile": "type_a_flat"},
    )
    assert resp.status_code == 200
    return resp.json()["batch_id"]


def test_confirm_import_api():
    batch_id = _upload_batch()
    resp = client.post(f"/api/import/batches/{batch_id}/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_id"] == batch_id
    assert data["status"] == "IMPORTED"
    assert "batch_no" in data


def test_confirm_import_api_not_found():
    resp = client.post("/api/import/batches/99999/confirm")
    assert resp.status_code == 400


def test_confirm_import_api_twice_fails():
    """Confirming an already-imported batch should fail."""
    batch_id = _upload_batch()
    resp1 = client.post(f"/api/import/batches/{batch_id}/confirm")
    assert resp1.status_code == 200

    resp2 = client.post(f"/api/import/batches/{batch_id}/confirm")
    assert resp2.status_code == 400
    assert "PARSED" in resp2.json()["detail"]


def test_import_detail_page():
    batch_id = _upload_batch()
    resp = client.get(f"/history-import/{batch_id}")
    assert resp.status_code == 200
    assert "导入详情" in resp.text


def test_import_detail_page_after_confirm():
    batch_id = _upload_batch()
    client.post(f"/api/import/batches/{batch_id}/confirm")
    resp = client.get(f"/history-import/{batch_id}")
    assert resp.status_code == 200
    assert "IMPORTED" in resp.text


def test_import_detail_page_not_found():
    resp = client.get("/history-import/99999")
    assert resp.status_code == 404


def test_import_detail_page_has_staging_records():
    batch_id = _upload_batch()
    resp = client.get(f"/history-import/{batch_id}")
    assert resp.status_code == 200
    # Should show staging records
    assert "物料1" in resp.text
    assert "物料2" in resp.text
    assert "客户A" in resp.text
