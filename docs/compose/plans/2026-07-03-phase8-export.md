# Phase 8: Excel 导出 Implementation Plan

**Goal:** 实现 Excel 导出功能，支持 4 个 Sheet：生产记录汇总、配方明细、识别审查、导入修正摘要。

## Global Constraints

- 使用 openpyxl 生成 xlsx
- 4 个 Sheet：生产记录汇总、配方明细、识别审查、导入修正摘要
- 导出文件保存到 `data/storage/exports/`
- 导出配置使用 `app/configs/export_config.yaml`

---

### Task 1: Excel 导出服务

**Covers:** [S11]

**Files:**
- Create: `app/infrastructure/excel/__init__.py`
- Create: `app/infrastructure/excel/exporter.py`
- Create: `app/tests/test_excel_exporter.py`

- [ ] **Step 1: 创建 Excel 导出器**

```python
# app/infrastructure/excel/exporter.py
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.settings import EXPORTS_DIR


HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)


def _style_header(ws, col_count):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER


def export_job_to_excel(job_id: int, data: dict) -> Path:
    """导出一个 job 的数据到 Excel"""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    # Sheet 1: 生产记录汇总
    ws1 = wb.active
    ws1.title = "生产记录汇总"
    headers1 = ["记录号", "时间", "客户", "产品", "颜色", "牌号"]
    ws1.append(headers1)
    _style_header(ws1, len(headers1))
    for rec in data.get("records", []):
        ws1.append([
            rec.get("index"), rec.get("time"), rec.get("customer"),
            rec.get("product"), rec.get("color"), rec.get("batch_no"),
        ])

    # Sheet 2: 配方明细
    ws2 = wb.create_sheet("配方明细")
    headers2 = ["记录号", "序号", "物料名称", "用量", "单位", "置信度"]
    ws2.append(headers2)
    _style_header(ws2, len(headers2))
    for item in data.get("materials", []):
        ws2.append([
            item.get("record_index"), item.get("seq"), item.get("material_name"),
            item.get("usage"), item.get("unit"), item.get("confidence"),
        ])

    # Sheet 3: 识别审查
    ws3 = wb.create_sheet("识别审查")
    headers3 = ["记录号", "字段", "OCR结果", "MiMo结果", "最终值", "置信度", "来源", "需确认"]
    ws3.append(headers3)
    _style_header(ws3, len(headers3))
    for f in data.get("fields", []):
        ws3.append([
            f.get("record_index"), f.get("field_key"), f.get("ocr_text"),
            f.get("mimo_text"), f.get("final_value"), f.get("confidence"),
            f.get("source"), "是" if f.get("need_review") else "否",
        ])

    # Sheet 4: 导入/修正摘要
    ws4 = wb.create_sheet("导入修正摘要")
    headers4 = ["类型", "记录号", "字段", "旧值", "新值", "操作时间"]
    ws4.append(headers4)
    _style_header(ws4, len(headers4))
    for log in data.get("corrections", []):
        ws4.append([
            log.get("type"), log.get("record_index"), log.get("field_key"),
            log.get("old_value"), log.get("new_value"), log.get("created_at"),
        ])

    # 自动列宽
    for ws in [ws1, ws2, ws3, ws4]:
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

    out_path = EXPORTS_DIR / f"job{job_id}_export.xlsx"
    wb.save(str(out_path))
    return out_path
```

- [ ] **Step 2: 编写测试**

```python
# app/tests/test_excel_exporter.py
import pytest
from pathlib import Path
from app.infrastructure.excel.exporter import export_job_to_excel


def test_export_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.infrastructure.excel.exporter.EXPORTS_DIR", tmp_path)
    data = {
        "records": [{"index": 1, "time": "08:30", "customer": "客户A", "product": "产品X", "color": "红", "batch_no": "B001"}],
        "materials": [{"record_index": 1, "seq": 1, "material_name": "PP", "usage": 100, "unit": "kg", "confidence": 0.9}],
        "fields": [{"record_index": 1, "field_key": "time", "ocr_text": "08:30", "mimo_text": "08:30", "final_value": "08:30", "confidence": 0.95, "source": "ocr", "need_review": False}],
        "corrections": [],
    }
    path = export_job_to_excel(1, data)
    assert path.exists()
    assert path.suffix == ".xlsx"


def test_export_sheets(tmp_path, monkeypatch):
    monkeypatch.setattr("app.infrastructure.excel.exporter.EXPORTS_DIR", tmp_path)
    from openpyxl import load_workbook
    data = {"records": [], "materials": [], "fields": [], "corrections": []}
    path = export_job_to_excel(1, data)
    wb = load_workbook(str(path))
    assert "生产记录汇总" in wb.sheetnames
    assert "配方明细" in wb.sheetnames
    assert "识别审查" in wb.sheetnames
    assert "导入修正摘要" in wb.sheetnames
```

- [ ] **Step 3: 运行测试并提交**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_excel_exporter.py -v
git add app/infrastructure/excel/ app/tests/test_excel_exporter.py
git commit -m "feat: Excel exporter with 4 sheets (records, materials, review, corrections)"
```

---

### Task 2: 导出服务和 API

**Covers:** [S11, S12]

**Files:**
- Create: `app/application/export_service.py`
- Modify: `app/interfaces/api_routes.py`
- Create: `app/tests/test_export_api.py`

- [ ] **Step 1: 创建导出服务**

```python
# app/application/export_service.py
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import (
    RecognitionJob, ProductionRecord, FieldRecognitionResult,
    ManualCorrectionLog, RecordMaterialItem,
)
from app.infrastructure.excel.exporter import export_job_to_excel


class ExportService:
    def export_job(self, job_id: int) -> dict:
        with get_session() as session:
            job = session.query(RecognitionJob).get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            records = session.query(ProductionRecord).filter_by(job_id=job_id).all()
            fields = session.query(FieldRecognitionResult).filter_by(job_id=job_id).all()
            corrections = session.query(ManualCorrectionLog).filter(
                ManualCorrectionLog.record_id.in_([r.id for r in records])
            ).all()
            materials = session.query(RecordMaterialItem).filter(
                RecordMaterialItem.record_id.in_([r.id for r in records])
            ).all()

        data = {
            "records": [
                {"index": r.record_index, "time": r.time_raw, "customer": r.customer_queue_raw,
                 "product": "", "color": r.color_raw, "batch_no": r.date_batch_no_raw}
                for r in records
            ],
            "materials": [
                {"record_index": m.record_id, "seq": m.seq, "material_name": m.material_name_raw,
                 "usage": m.usage_value, "unit": m.unit_raw, "confidence": m.confidence}
                for m in materials
            ],
            "fields": [
                {"record_index": f.record_id, "field_key": f.field_key, "ocr_text": f.ocr_raw_text,
                 "mimo_text": f.mimo_raw_text, "final_value": f.final_value,
                 "confidence": f.final_confidence, "source": f.source, "need_review": f.need_review}
                for f in fields
            ],
            "corrections": [
                {"type": c.correction_type, "record_index": c.record_id, "field_key": c.field_key,
                 "old_value": c.old_value, "new_value": c.new_value, "created_at": str(c.created_at)}
                for c in corrections
            ],
        }

        path = export_job_to_excel(job_id, data)

        with get_session() as session:
            job = session.query(RecognitionJob).get(job_id)
            job.export_path = str(path)
            job.status = "EXPORTED"

        return {"job_id": job_id, "export_path": str(path)}
```

- [ ] **Step 2: 添加导出 API**

```python
from app.application.export_service import ExportService
export_service = ExportService()

@router.post("/jobs/{job_id}/export")
async def export_job(job_id: int):
    try:
        result = export_service.export_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 3: 编写测试并提交**

```python
# app/tests/test_export_api.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@patch("app.interfaces.api_routes.export_service")
def test_export_job(mock_service):
    mock_service.export_job.return_value = {"job_id": 1, "export_path": "/tmp/test.xlsx"}
    resp = client.post("/api/jobs/1/export")
    assert resp.status_code == 200
```

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_export_api.py -v
git add app/application/export_service.py app/interfaces/api_routes.py app/tests/test_export_api.py
git commit -m "feat: export service and API endpoint"
```
