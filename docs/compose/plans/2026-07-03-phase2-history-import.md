# Phase 2: 历史电子记录导入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现历史电子生产记录（xlsx/csv）的导入功能：上传 → 解析 → staging 暂存 → 预览校验 → 确认写入正式库，同时自动提取客户库、产品库、物料库、配方库。

**Architecture:** 分层架构。Infrastructure 层负责 Excel/CSV 解析（openpyxl + csv），Application 层负责导入业务流程编排（staging → validation → commit），Interface 层提供上传/预览/确认的 Web 页面和 API。使用 import profile 配置适配不同格式。

**Tech Stack:** openpyxl（xlsx 解析）, csv（csv 解析）, FastAPI（API + Web）, SQLAlchemy（ORM）, Jinja2（模板）

## Global Constraints

- 使用已有的 4 张导入表：import_batches, import_staging_records, import_staging_material_items, import_staging_warnings
- 导入文件存储在 `data/storage/history_imports/`
- staging 暂存区数据在用户确认前不写入正式库
- 确认时自动提取：customers, products, materials, formulas, formula_items
- 物料名模糊匹配已有物料库，新物料自动创建
- 支持 xlsx 和 csv 两种格式
- 每次导入生成唯一 batch_no（格式：IMP%Y%m%d%H%M%S）
- 配置使用 `app/configs/import_profiles.yaml`

---

### Task 1: 导入配置文件与解析器基础

**Covers:** [S9, S13]

**Files:**
- Create: `app/configs/import_profiles.yaml`
- Create: `app/infrastructure/history_import/__init__.py`
- Create: `app/infrastructure/history_import/file_parser.py`
- Create: `app/tests/test_import_parser.py`

**Interfaces:**
- Produces: `load_import_profiles() -> dict` 导入配置加载
- Produces: `parse_file(file_path, profile) -> list[dict]` 文件解析，返回原始行列表

- [ ] **Step 1: 创建导入配置文件**

```yaml
# app/configs/import_profiles.yaml
profiles:
  type_a_flat:
    name: "扁平表格（一行一条记录）"
    description: "每行是一条完整的生产记录，包含客户、产品、物料等信息"
    file_types: ["xlsx", "csv"]
    header_row: 1  # 表头行号（1-based）
    data_start_row: 2  # 数据起始行
    columns:
      date:
        header: ["日期", "生产日期", "Date"]
        type: date
        required: true
      time:
        header: ["时间", "班次", "Time"]
        type: text
        required: false
      customer:
        header: ["客户", "客户名称", "Customer"]
        type: text
        required: true
      product:
        header: ["产品", "排号", "产品名称", "Product"]
        type: text
        required: true
      color:
        header: ["颜色", "色号", "Color"]
        type: text
        required: false
      batch_no:
        header: ["牌号", "批号", "Batch"]
        type: text
        required: false
      material_name:
        header: ["物料", "物料名称", "原料", "Material"]
        type: text
        required: true
      usage:
        header: ["用量", "使用量", "Usage"]
        type: number
        required: true
      unit:
        header: ["单位", "Unit"]
        type: text
        required: false
        default: "kg"
      main_speed:
        header: ["主机转速", "主速"]
        type: number
        required: false
      feeder_speed:
        header: ["喂料转速", "喂速"]
        type: number
        required: false

  type_b_template:
    name: "固定模板（类似纸质版排版）"
    description: "类似手写记录的电子版，每3条记录为一组"
    file_types: ["xlsx"]
    header_row: 1
    data_start_row: 2
    columns:
      date:
        header: ["日期", "生产日期"]
        type: date
        required: true
      record_group:
        header: ["记录组"]
        type: number
        required: true
      time_1:
        header: ["时间1"]
        type: text
        required: false
      customer_1:
        header: ["客户1"]
        type: text
        required: false
      material_1_name:
        header: ["物料1名称"]
        type: text
        required: false
      material_1_usage:
        header: ["物料1用量"]
        type: number
        required: false
      # ... 更多字段按需扩展
```

- [ ] **Step 2: 创建导入配置加载函数**

```python
# app/infrastructure/history_import/__init__.py
from app.configs import load_config

def load_import_profiles() -> dict:
    return load_config("import_profiles")
```

- [ ] **Step 3: 创建文件解析器**

```python
# app/infrastructure/history_import/file_parser.py
import csv
from pathlib import Path
from openpyxl import load_workbook


def parse_xlsx(file_path: Path, profile: dict) -> list[dict]:
    """解析 xlsx 文件，返回原始行数据列表"""
    wb = load_workbook(str(file_path), read_only=True, data_only=True)
    ws = wb.active

    header_row = profile.get("header_row", 1)
    data_start_row = profile.get("data_start_row", 2)

    # 读取表头
    headers = []
    for cell in ws[header_row]:
        headers.append(str(cell.value).strip() if cell.value else "")

    # 构建列名到索引的映射
    col_map = _build_column_map(headers, profile["columns"])

    # 读取数据行
    rows = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=data_start_row, values_only=True), start=data_start_row):
        row_data = {"_source_row": row_idx}
        for field_key, col_idx in col_map.items():
            if col_idx is not None and col_idx < len(row):
                row_data[field_key] = row[col_idx]
            else:
                row_data[field_key] = None
        # 跳过空行
        if all(v is None for k, v in row_data.items() if not k.startswith("_")):
            continue
        rows.append(row_data)

    wb.close()
    return rows


def parse_csv(file_path: Path, profile: dict) -> list[dict]:
    """解析 csv 文件，返回原始行数据列表"""
    header_row = profile.get("header_row", 1)
    data_start_row = profile.get("data_start_row", 2)

    rows = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = []
        for i, row in enumerate(reader, start=1):
            if i == header_row:
                headers = [cell.strip() for cell in row]
                continue
            if i < data_start_row:
                continue

            col_map = _build_column_map(headers, profile["columns"])
            row_data = {"_source_row": i}
            for field_key, col_idx in col_map.items():
                if col_idx is not None and col_idx < len(row):
                    row_data[field_key] = row[col_idx].strip() if row[col_idx] else None
                else:
                    row_data[field_key] = None

            if all(v is None for k, v in row_data.items() if not k.startswith("_")):
                continue
            rows.append(row_data)

    return rows


def _build_column_map(headers: list[str], columns: dict) -> dict[str, int | None]:
    """将 profile 中的列配置映射到实际表头索引"""
    col_map = {}
    for field_key, col_config in columns.items():
        found_idx = None
        for alias in col_config["header"]:
            alias_lower = alias.lower()
            for idx, h in enumerate(headers):
                if h.lower() == alias_lower:
                    found_idx = idx
                    break
            if found_idx is not None:
                break
        col_map[field_key] = found_idx
    return col_map


def parse_file(file_path: Path, profile: dict) -> list[dict]:
    """根据文件扩展名选择解析器"""
    ext = file_path.suffix.lower()
    if ext == ".xlsx":
        return parse_xlsx(file_path, profile)
    elif ext == ".csv":
        return parse_csv(file_path, profile)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
```

- [ ] **Step 4: 编写解析器测试**

```python
# app/tests/test_import_parser.py
import csv
import pytest
from pathlib import Path
from openpyxl import Workbook

from app.infrastructure.history_import.file_parser import parse_file


@pytest.fixture
def flat_profile():
    return {
        "header_row": 1,
        "data_start_row": 2,
        "columns": {
            "date": {"header": ["日期"], "type": "date", "required": True},
            "customer": {"header": ["客户"], "type": "text", "required": True},
            "product": {"header": ["产品"], "type": "text", "required": True},
            "material_name": {"header": ["物料"], "type": "text", "required": True},
            "usage": {"header": ["用量"], "type": "number", "required": True},
            "unit": {"header": ["单位"], "type": "text", "required": False, "default": "kg"},
        },
    }


@pytest.fixture
def sample_xlsx(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "物料", "用量", "单位"])
    ws.append(["2026-01-01", "客户A", "产品X", "PP原料", 100, "kg"])
    ws.append(["2026-01-01", "客户A", "产品X", "PE原料", 50, "kg"])
    ws.append(["2026-01-02", "客户B", "产品Y", "色母粒", 10, "kg"])
    path = tmp_path / "test.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def sample_csv(tmp_path):
    path = tmp_path / "test.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["日期", "客户", "产品", "物料", "用量", "单位"])
        writer.writerow(["2026-01-01", "客户A", "产品X", "PP原料", "100", "kg"])
        writer.writerow(["2026-01-02", "客户B", "产品Y", "色母粒", "10", "kg"])
    return path


def test_parse_xlsx(sample_xlsx, flat_profile):
    rows = parse_file(sample_xlsx, flat_profile)
    assert len(rows) == 3
    assert rows[0]["customer"] == "客户A"
    assert rows[0]["material_name"] == "PP原料"
    assert rows[0]["usage"] == 100


def test_parse_csv(sample_csv, flat_profile):
    rows = parse_file(sample_csv, flat_profile)
    assert len(rows) == 2
    assert rows[0]["customer"] == "客户A"
    assert rows[1]["material_name"] == "色母粒"


def test_parse_xlsx_skip_empty_rows(tmp_path, flat_profile):
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "物料", "用量", "单位"])
    ws.append(["2026-01-01", "客户A", "产品X", "PP原料", 100, "kg"])
    ws.append([None, None, None, None, None, None])  # 空行
    ws.append(["2026-01-02", "客户B", "产品Y", "色母粒", 10, "kg"])
    path = tmp_path / "test_empty.xlsx"
    wb.save(str(path))
    rows = parse_file(path, flat_profile)
    assert len(rows) == 2


def test_parse_unsupported_format(tmp_path, flat_profile):
    path = tmp_path / "test.txt"
    path.write_text("not a spreadsheet")
    with pytest.raises(ValueError, match="不支持的文件格式"):
        parse_file(path, flat_profile)
```

- [ ] **Step 5: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_import_parser.py -v
```

Expected: 4 tests PASS

- [ ] **Step 6: 提交**

```bash
git add app/configs/import_profiles.yaml app/infrastructure/history_import/ app/tests/test_import_parser.py
git commit -m "feat: import file parser with xlsx/csv support"
```

---

### Task 2: 导入服务 — staging 暂存

**Covers:** [S9, S6]

**Files:**
- Create: `app/application/import_service.py`
- Create: `app/tests/test_import_service.py`

**Interfaces:**
- Consumes: `parse_file(file_path, profile)` from Task 1
- Produces: `ImportService.upload_and_parse(file, profile_name) -> ImportBatch` 上传并解析到 staging
- Produces: `ImportService.get_batch(batch_id) -> ImportBatch` 获取批次详情
- Produces: `ImportService.list_batches() -> list[ImportBatch]` 列出所有批次

- [ ] **Step 1: 编写导入服务测试**

```python
# app/tests/test_import_service.py
import csv
import io
import pytest
from pathlib import Path
from openpyxl import Workbook

from app.application.import_service import ImportService
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import ImportBatch, ImportStagingRecord


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def service():
    return ImportService()


@pytest.fixture
def sample_xlsx_file(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "物料", "用量", "单位"])
    ws.append(["2026-01-01", "客户A", "产品X", "PP原料", 100, "kg"])
    ws.append(["2026-01-01", "客户A", "产品X", "PE原料", 50, "kg"])
    path = tmp_path / "history.xlsx"
    wb.save(str(path))
    return path


def test_upload_and_parse_creates_batch(service, sample_xlsx_file):
    batch = service.upload_and_parse(sample_xlsx_file, "type_a_flat")
    assert batch.id is not None
    assert batch.batch_no.startswith("IMP")
    assert batch.status == "PARSED"
    assert batch.total_rows == 2


def test_upload_and_parse_creates_staging_records(service, sample_xlsx_file):
    batch = service.upload_and_parse(sample_xlsx_file, "type_a_flat")
    with get_session() as session:
        records = session.query(ImportStagingRecord).filter_by(batch_id=batch.id).all()
        assert len(records) == 2
        assert records[0].is_valid is True
        assert records[0].normalized_payload_json["customer"] == "客户A"


def test_list_batches(service, sample_xlsx_file):
    service.upload_and_parse(sample_xlsx_file, "type_a_flat")
    batches = service.list_batches()
    assert len(batches) == 1


def test_get_batch(service, sample_xlsx_file):
    batch = service.upload_and_parse(sample_xlsx_file, "type_a_flat")
    fetched = service.get_batch(batch.id)
    assert fetched is not None
    assert fetched.batch_no == batch.batch_no
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_import_service.py -v
```

Expected: FAIL (ImportService not defined)

- [ ] **Step 3: 实现导入服务**

```python
# app/application/import_service.py
import datetime
import shutil
from pathlib import Path

from app.configs import load_config
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import (
    ImportBatch,
    ImportStagingRecord,
    ImportStagingMaterialItem,
    ImportStagingWarning,
)
from app.infrastructure.history_import.file_parser import parse_file
from app.settings import HISTORY_IMPORTS_DIR


class ImportService:
    def __init__(self):
        self._profiles = None

    @property
    def profiles(self) -> dict:
        if self._profiles is None:
            self._profiles = load_config("import_profiles")
        return self._profiles

    def _generate_batch_no(self) -> str:
        return datetime.datetime.now().strftime("IMP%Y%m%d%H%M%S")

    def upload_and_parse(self, file_path: Path, profile_name: str) -> ImportBatch:
        """上传文件并解析到 staging 暂存区"""
        profile = self.profiles["profiles"][profile_name]

        # 复制文件到导入目录
        HISTORY_IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = HISTORY_IMPORTS_DIR / file_path.name
        shutil.copy2(str(file_path), str(dest_path))

        # 解析文件
        raw_rows = parse_file(file_path, profile)

        # 创建批次
        batch_no = self._generate_batch_no()
        with get_session() as session:
            batch = ImportBatch(
                batch_no=batch_no,
                source_file_path=str(dest_path),
                source_file_name=file_path.name,
                import_profile=profile_name,
                status="PARSED",
                total_rows=len(raw_rows),
                valid_rows=len(raw_rows),
                invalid_rows=0,
            )
            session.add(batch)
            session.flush()
            batch_id = batch.id

            # 写入 staging 记录
            for idx, raw_row in enumerate(raw_rows, start=1):
                normalized = self._normalize_row(raw_row, profile)
                staging = ImportStagingRecord(
                    batch_id=batch_id,
                    source_sheet=file_path.stem,
                    source_row_start=raw_row.get("_source_row", idx),
                    record_index=idx,
                    raw_payload_json={k: v for k, v in raw_row.items() if not k.startswith("_")},
                    normalized_payload_json=normalized,
                    is_valid=True,
                    is_selected=True,
                )
                session.add(staging)

        # 重新获取 batch（避免 DetachedInstanceError）
        with get_session() as session:
            return session.query(ImportBatch).get(batch_id)

    def _normalize_row(self, raw_row: dict, profile: dict) -> dict:
        """将原始行数据标准化"""
        normalized = {}
        for field_key, col_config in profile["columns"].items():
            value = raw_row.get(field_key)
            if value is not None:
                normalized[field_key] = str(value).strip()
            elif "default" in col_config:
                normalized[field_key] = col_config["default"]
            else:
                normalized[field_key] = None
        return normalized

    def get_batch(self, batch_id: int) -> ImportBatch | None:
        with get_session() as session:
            return session.query(ImportBatch).get(batch_id)

    def list_batches(self) -> list[ImportBatch]:
        with get_session() as session:
            return (
                session.query(ImportBatch)
                .order_by(ImportBatch.created_at.desc())
                .all()
            )
```

- [ ] **Step 4: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_import_service.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/application/import_service.py app/tests/test_import_service.py
git commit -m "feat: import service with staging area"
```

---

### Task 3: 导入 API 端点

**Covers:** [S9, S12]

**Files:**
- Create: `app/interfaces/import_routes.py`
- Modify: `app/main.py` (添加 import_router)
- Create: `app/tests/test_import_api.py`

**Interfaces:**
- Consumes: `ImportService` from Task 2
- Produces: `POST /api/import/upload` 上传导入文件
- Produces: `GET /api/import/batches` 导入批次列表
- Produces: `GET /api/import/batches/{batch_id}` 批次详情（含 staging 记录）

- [ ] **Step 1: 创建导入 API 路由**

```python
# app/interfaces/import_routes.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import tempfile

from app.application.import_service import ImportService

router = APIRouter()
import_service = ImportService()


@router.post("/upload")
async def upload_import_file(
    file: UploadFile = File(...),
    profile: str = Form("type_a_flat"),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".csv"):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        batch = import_service.upload_and_parse(tmp_path, profile)
        return {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "status": batch.status,
            "total_rows": batch.total_rows,
            "valid_rows": batch.valid_rows,
            "invalid_rows": batch.invalid_rows,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/batches")
async def list_import_batches():
    batches = import_service.list_batches()
    return [
        {
            "id": b.id,
            "batch_no": b.batch_no,
            "source_file_name": b.source_file_name,
            "import_profile": b.import_profile,
            "status": b.status,
            "total_rows": b.total_rows,
            "valid_rows": b.valid_rows,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in batches
    ]


@router.get("/batches/{batch_id}")
async def get_import_batch(batch_id: int):
    batch = import_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {
        "id": batch.id,
        "batch_no": batch.batch_no,
        "source_file_name": batch.source_file_name,
        "import_profile": batch.import_profile,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "invalid_rows": batch.invalid_rows,
        "staging_records": [
            {
                "id": sr.id,
                "record_index": sr.record_index,
                "raw_payload": sr.raw_payload_json,
                "normalized_payload": sr.normalized_payload_json,
                "is_valid": sr.is_valid,
                "is_selected": sr.is_selected,
            }
            for sr in (batch.staging_records or [])
        ],
    }
```

- [ ] **Step 2: 注册路由到 main.py**

在 `app/main.py` 中添加：

```python
from app.interfaces.import_routes import router as import_router
app.include_router(import_router, prefix="/api/import")
```

- [ ] **Step 3: 编写 API 测试**

```python
# app/tests/test_import_api.py
import io
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _make_xlsx_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "物料", "用量", "单位"])
    ws.append(["2026-01-01", "客户A", "产品X", "PP原料", 100, "kg"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def test_upload_import_file():
    xlsx_bytes = _make_xlsx_bytes()
    resp = client.post(
        "/api/import/upload",
        files={"file": ("history.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"profile": "type_a_flat"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PARSED"
    assert data["total_rows"] == 1


def test_upload_unsupported_format():
    resp = client.post(
        "/api/import/upload",
        files={"file": ("test.txt", b"not a spreadsheet", "text/plain")},
        data={"profile": "type_a_flat"},
    )
    assert resp.status_code == 400


def test_list_import_batches():
    # 先上传一个文件
    xlsx_bytes = _make_xlsx_bytes()
    client.post(
        "/api/import/upload",
        files={"file": ("history.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"profile": "type_a_flat"},
    )
    resp = client.get("/api/import/batches")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
```

- [ ] **Step 4: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_import_api.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/interfaces/import_routes.py app/main.py app/tests/test_import_api.py
git commit -m "feat: import API endpoints"
```

---

### Task 4: 导入 Web 页面（上传 + 列表）

**Covers:** [S9, S12]

**Files:**
- Create: `app/interfaces/templates/history_import.html`
- Modify: `app/interfaces/web_routes.py` (添加导入页面路由)

**Interfaces:**
- Consumes: `ImportService` from Task 2
- Produces: `GET /history-import` 导入管理页面

- [ ] **Step 1: 添加 Web 路由**

在 `app/interfaces/web_routes.py` 中添加：

```python
from app.application.import_service import ImportService
import_service = ImportService()

@router.get("/history-import")
async def history_import_page(request: Request):
    batches = import_service.list_batches()
    return templates.TemplateResponse("history_import.html", {
        "request": request,
        "title": "历史记录导入",
        "batches": batches,
    })
```

- [ ] **Step 2: 创建导入页面模板**

```html
<!-- app/interfaces/templates/history_import.html -->
{% extends "base.html" %}
{% block content %}
<div class="page-header">
    <h1>历史记录导入</h1>
</div>

<div class="card" style="margin-bottom:24px">
    <h3>上传历史文件</h3>
    <p style="color:#666; margin-bottom:16px">支持 xlsx 和 csv 格式，上传后系统自动解析到暂存区</p>
    <form id="import-form" enctype="multipart/form-data" style="display:flex; gap:12px; align-items:center; flex-wrap:wrap">
        <input type="file" name="file" accept=".xlsx,.csv" required>
        <select name="profile">
            <option value="type_a_flat">扁平表格（一行一条记录）</option>
            <option value="type_b_template">固定模板（类似纸质版）</option>
        </select>
        <button type="submit" class="btn btn-success">上传并解析</button>
    </form>
    <div id="upload-result" style="margin-top:12px; display:none"></div>
</div>

<div class="card">
    <h3>导入批次</h3>
    <table>
        <thead>
            <tr>
                <th>批次号</th>
                <th>文件名</th>
                <th>格式</th>
                <th>状态</th>
                <th>记录数</th>
                <th>创建时间</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for batch in batches %}
            <tr>
                <td>{{ batch.batch_no }}</td>
                <td>{{ batch.source_file_name or '-' }}</td>
                <td>{{ batch.import_profile }}</td>
                <td><span class="status-{{ batch.status.lower() }}">{{ batch.status }}</span></td>
                <td>{{ batch.total_rows or 0 }}</td>
                <td>{{ batch.created_at.strftime('%Y-%m-%d %H:%M') if batch.created_at else '-' }}</td>
                <td><a href="/history-import/{{ batch.id }}" class="btn">查看</a></td>
            </tr>
            {% endfor %}
            {% if not batches %}
            <tr><td colspan="7" style="text-align:center; color:#999">暂无导入记录</td></tr>
            {% endif %}
        </tbody>
    </table>
</div>

<script>
document.getElementById('import-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const resultDiv = document.getElementById('upload-result');
    try {
        const resp = await fetch('/api/import/upload', { method: 'POST', body: formData });
        if (resp.ok) {
            const data = await resp.json();
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<span style="color:green">解析成功: ' + data.total_rows + ' 条记录</span>';
            setTimeout(() => window.location.reload(), 1500);
        } else {
            const err = await resp.json();
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<span style="color:red">上传失败: ' + (err.detail || '未知错误') + '</span>';
        }
    } catch (err) {
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<span style="color:red">上传失败: ' + err.message + '</span>';
    }
});
</script>

<style>
.status-parsed { color: #2563eb; }
.status-confirmed { color: #16a34a; }
.status-imported { color: #16a34a; }
.status-failed { color: #dc2626; }
select { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
</style>
{% endblock %}
```

- [ ] **Step 3: 运行全部测试确认无回归**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/ -v
```

Expected: All tests PASS (原有 13 + 新增 ~11)

- [ ] **Step 4: 提交**

```bash
git add app/interfaces/templates/history_import.html app/interfaces/web_routes.py
git commit -m "feat: history import web page"
```

---

### Task 5: 导入确认 — staging 写入正式库

**Covers:** [S9, S6]

**Files:**
- Modify: `app/application/import_service.py` (添加 confirm_and_import)
- Create: `app/tests/test_import_confirm.py`

**Interfaces:**
- Consumes: `ImportStagingRecord` data from staging tables
- Produces: `ImportService.confirm_and_import(batch_id) -> ImportBatch` 确认导入，写入正式库
- Produces: 自动提取 customers, products, materials, formulas, formula_items

- [ ] **Step 1: 编写确认导入测试**

```python
# app/tests/test_import_confirm.py
import pytest
from pathlib import Path
from openpyxl import Workbook

from app.application.import_service import ImportService
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import (
    ImportBatch,
    Customer,
    Product,
    Material,
    Formula,
    FormulaItem,
)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def service():
    return ImportService()


@pytest.fixture
def parsed_batch(service, tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "物料", "用量", "单位"])
    ws.append(["2026-01-01", "客户A", "产品X", "PP原料", 100, "kg"])
    ws.append(["2026-01-01", "客户A", "产品X", "PE原料", 50, "kg"])
    ws.append(["2026-01-02", "客户B", "产品Y", "色母粒", 10, "kg"])
    path = tmp_path / "history.xlsx"
    wb.save(str(path))
    return service.upload_and_parse(path, "type_a_flat")


def test_confirm_creates_customers(service, parsed_batch):
    batch = service.confirm_and_import(parsed_batch.id)
    assert batch.status == "IMPORTED"
    with get_session() as session:
        customers = session.query(Customer).all()
        names = {c.customer_name for c in customers}
        assert "客户A" in names
        assert "客户B" in names


def test_confirm_creates_products(service, parsed_batch):
    service.confirm_and_import(parsed_batch.id)
    with get_session() as session:
        products = session.query(Product).all()
        names = {p.product_name for p in products}
        assert "产品X" in names
        assert "产品Y" in names


def test_confirm_creates_materials(service, parsed_batch):
    service.confirm_and_import(parsed_batch.id)
    with get_session() as session:
        materials = session.query(Material).all()
        names = {m.standard_name for m in materials}
        assert "PP原料" in names
        assert "PE原料" in names
        assert "色母粒" in names


def test_confirm_creates_formulas(service, parsed_batch):
    service.confirm_and_import(parsed_batch.id)
    with get_session() as session:
        formulas = session.query(Formula).all()
        # 客户A+产品X 有2个物料，应创建1个配方
        assert len(formulas) >= 1
        formula = formulas[0]
        items = session.query(FormulaItem).filter_by(formula_id=formula.id).all()
        assert len(items) == 2  # PP原料 + PE原料


def test_confirm_idempotent(service, parsed_batch):
    """重复确认不会创建重复数据"""
    service.confirm_and_import(parsed_batch.id)
    # 第二次确认应该跳过（状态已为 IMPORTED）
    batch = service.get_batch(parsed_batch.id)
    assert batch.status == "IMPORTED"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_import_confirm.py -v
```

Expected: FAIL (confirm_and_import not defined)

- [ ] **Step 3: 实现确认导入逻辑**

在 `app/application/import_service.py` 中添加以下方法：

```python
from app.infrastructure.database.models import Customer, Product, Material, Formula, FormulaItem
from app.infrastructure.storage.path_manager import calculate_file_hash

def confirm_and_import(self, batch_id: int) -> ImportBatch:
    """确认导入，将 staging 数据写入正式库"""
    with get_session() as session:
        batch = session.query(ImportBatch).get(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")
        if batch.status == "IMPORTED":
            return batch
        if batch.status != "PARSED":
            raise ValueError(f"Cannot import batch in status: {batch.status}")

        staging_records = (
            session.query(ImportStagingRecord)
            .filter_by(batch_id=batch_id, is_valid=True, is_selected=True)
            .all()
        )

        # 按 客户+产品 分组，构建配方
        groups: dict[tuple, list] = {}
        for sr in staging_records:
            p = sr.normalized_payload_json
            key = (p.get("customer"), p.get("product"), p.get("color"), p.get("batch_no"))
            groups.setdefault(key, []).append(sr)

        for (customer_name, product_name, color, batch_no_key), records in groups.items():
            # 获取或创建客户
            customer = self._get_or_create_customer(session, customer_name)
            # 获取或创建产品
            product = self._get_or_create_product(session, customer.id, product_name)

            # 收集物料
            material_items = []
            for sr in records:
                p = sr.normalized_payload_json
                mat_name = p.get("material_name")
                if not mat_name:
                    continue
                material = self._get_or_create_material(session, mat_name)
                usage_raw = p.get("usage")
                usage_value = float(usage_raw) if usage_raw else None
                unit_raw = p.get("unit", "kg")
                material_items.append({
                    "material_id": material.id,
                    "usage_value": usage_value,
                    "unit_raw": unit_raw,
                })

            # 创建配方
            if material_items:
                fp_input = f"{customer_name}:{product_name}:{color or ''}"
                import hashlib
                fp = hashlib.md5(fp_input.encode()).hexdigest()[:32]

                formula = Formula(
                    customer_id=customer.id,
                    product_id=product.id,
                    color=color,
                    formula_name=f"{customer_name}-{product_name}" + (f"-{color}" if color else ""),
                    formula_fingerprint=fp,
                    created_from_import_batch_id=batch_id,
                )
                session.add(formula)
                session.flush()

                for seq, item in enumerate(material_items, start=1):
                    fi = FormulaItem(
                        formula_id=formula.id,
                        seq=seq,
                        material_id=item["material_id"],
                        usage_value=item["usage_value"],
                        unit_raw=item["unit_raw"],
                        unit_standard=item["unit_raw"],
                    )
                    session.add(fi)

        batch.status = "IMPORTED"
        batch.confirmed_at = func.now()

    with get_session() as session:
        return session.query(ImportBatch).get(batch_id)


def _get_or_create_customer(self, session, name: str) -> Customer:
    customer = session.query(Customer).filter_by(customer_name=name).first()
    if not customer:
        customer = Customer(customer_name=name)
        session.add(customer)
        session.flush()
    return customer


def _get_or_create_product(self, session, customer_id: int, name: str) -> Product:
    product = session.query(Product).filter_by(customer_id=customer_id, product_name=name).first()
    if not product:
        product = Product(customer_id=customer_id, product_name=name)
        session.add(product)
        session.flush()
    return product


def _get_or_create_material(self, session, name: str) -> Material:
    material = session.query(Material).filter_by(standard_name=name).first()
    if not material:
        material = Material(standard_name=name)
        session.add(material)
        session.flush()
    return material
```

注意：需要在文件顶部导入 `func`：`from sqlalchemy import func`

- [ ] **Step 4: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_import_confirm.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: 运行全部测试确认无回归**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/ -v
```

Expected: All tests PASS

- [ ] **Step 6: 提交**

```bash
git add app/application/import_service.py app/tests/test_import_confirm.py
git commit -m "feat: import confirm - staging to production tables"
```

---

### Task 6: 导入确认 API 与页面

**Covers:** [S9, S12]

**Files:**
- Modify: `app/interfaces/import_routes.py` (添加确认端点)
- Create: `app/interfaces/templates/import_detail.html`
- Modify: `app/interfaces/web_routes.py` (添加详情页路由)
- Create: `app/tests/test_import_confirm_api.py`

**Interfaces:**
- Consumes: `ImportService.confirm_and_import` from Task 5
- Produces: `POST /api/import/batches/{batch_id}/confirm` 确认导入
- Produces: `GET /history-import/{batch_id}` 导入详情页面

- [ ] **Step 1: 添加确认 API 端点**

在 `app/interfaces/import_routes.py` 中添加：

```python
@router.post("/batches/{batch_id}/confirm")
async def confirm_import(batch_id: int):
    try:
        batch = import_service.confirm_and_import(batch_id)
        return {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "status": batch.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: 添加 Web 路由**

在 `app/interfaces/web_routes.py` 中添加：

```python
@router.get("/history-import/{batch_id}")
async def import_detail_page(request: Request, batch_id: int):
    batch = import_service.get_batch(batch_id)
    if not batch:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Batch not found")
    return templates.TemplateResponse("import_detail.html", {
        "request": request,
        "title": f"导入详情 - {batch.batch_no}",
        "batch": batch,
    })
```

- [ ] **Step 3: 创建详情页模板**

```html
<!-- app/interfaces/templates/import_detail.html -->
{% extends "base.html" %}
{% block content %}
<div class="page-header">
    <h1>导入详情: {{ batch.batch_no }}</h1>
    <a href="/history-import" class="btn">返回列表</a>
</div>

<div class="detail-grid">
    <div class="detail-card">
        <h3>基本信息</h3>
        <table>
            <tr><td>批次号</td><td>{{ batch.batch_no }}</td></tr>
            <tr><td>文件名</td><td>{{ batch.source_file_name or '-' }}</td></tr>
            <tr><td>格式</td><td>{{ batch.import_profile }}</td></tr>
            <tr><td>状态</td><td><span class="status-{{ batch.status.lower() }}">{{ batch.status }}</span></td></tr>
            <tr><td>总记录数</td><td>{{ batch.total_rows or 0 }}</td></tr>
            <tr><td>有效记录</td><td>{{ batch.valid_rows or 0 }}</td></tr>
            <tr><td>创建时间</td><td>{{ batch.created_at.strftime('%Y-%m-%d %H:%M:%S') if batch.created_at else '-' }}</td></tr>
            {% if batch.confirmed_at %}
            <tr><td>确认时间</td><td>{{ batch.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') }}</td></tr>
            {% endif %}
        </table>

        {% if batch.status == 'PARSED' %}
        <div style="margin-top:16px">
            <button id="confirm-btn" class="btn btn-success" onclick="confirmImport()">确认导入</button>
            <span id="confirm-result" style="margin-left:12px"></span>
        </div>
        {% endif %}
    </div>
</div>

<div class="card" style="margin-top:24px">
    <h3>暂存记录</h3>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>日期</th>
                <th>客户</th>
                <th>产品</th>
                <th>物料</th>
                <th>用量</th>
                <th>状态</th>
            </tr>
        </thead>
        <tbody>
            {% for sr in batch.staging_records or [] %}
            <tr>
                <td>{{ sr.record_index }}</td>
                <td>{{ sr.normalized_payload_json.get('date', '-') if sr.normalized_payload_json else '-' }}</td>
                <td>{{ sr.normalized_payload_json.get('customer', '-') if sr.normalized_payload_json else '-' }}</td>
                <td>{{ sr.normalized_payload_json.get('product', '-') if sr.normalized_payload_json else '-' }}</td>
                <td>{{ sr.normalized_payload_json.get('material_name', '-') if sr.normalized_payload_json else '-' }}</td>
                <td>{{ sr.normalized_payload_json.get('usage', '-') if sr.normalized_payload_json else '-' }} {{ sr.normalized_payload_json.get('unit', '') if sr.normalized_payload_json else '' }}</td>
                <td>{{ '有效' if sr.is_valid else '无效' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<script>
async function confirmImport() {
    if (!confirm('确认导入？将把暂存数据写入正式库。')) return;
    const btn = document.getElementById('confirm-btn');
    const result = document.getElementById('confirm-result');
    btn.disabled = true;
    try {
        const resp = await fetch('/api/import/batches/{{ batch.id }}/confirm', { method: 'POST' });
        if (resp.ok) {
            result.innerHTML = '<span style="color:green">导入成功！</span>';
            setTimeout(() => window.location.reload(), 1500);
        } else {
            const err = await resp.json();
            result.innerHTML = '<span style="color:red">失败: ' + (err.detail || '未知错误') + '</span>';
            btn.disabled = false;
        }
    } catch (e) {
        result.innerHTML = '<span style="color:red">失败: ' + e.message + '</span>';
        btn.disabled = false;
    }
}
</script>

<style>
.detail-grid { display: grid; grid-template-columns: 1fr; gap: 20px; }
.detail-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.detail-card table td:first-child { font-weight: 600; padding-right: 16px; width: 120px; }
</style>
{% endblock %}
```

- [ ] **Step 4: 编写确认 API 测试**

```python
# app/tests/test_import_confirm_api.py
import io
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import ImportBatch

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _upload_test_file() -> int:
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "物料", "用量", "单位"])
    ws.append(["2026-01-01", "客户A", "产品X", "PP原料", 100, "kg"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = client.post(
        "/api/import/upload",
        files={"file": ("history.xlsx", buf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"profile": "type_a_flat"},
    )
    return resp.json()["batch_id"]


def test_confirm_import():
    batch_id = _upload_test_file()
    resp = client.post(f"/api/import/batches/{batch_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["status"] == "IMPORTED"


def test_confirm_import_page():
    batch_id = _upload_test_file()
    resp = client.get(f"/history-import/{batch_id}")
    assert resp.status_code == 200
    assert "导入详情" in resp.text
```

- [ ] **Step 5: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_import_confirm_api.py -v
```

Expected: 2 tests PASS

- [ ] **Step 6: 运行全部测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/ -v
```

Expected: All tests PASS

- [ ] **Step 7: 提交**

```bash
git add app/interfaces/import_routes.py app/interfaces/web_routes.py app/interfaces/templates/import_detail.html app/tests/test_import_confirm_api.py
git commit -m "feat: import confirm API and detail page"
```

---

### Task 7: Phase 2 完整验证

**Covers:** [S12, S14]

**Files:**
- Verify all tests pass
- Verify application starts and import flow works end-to-end

- [ ] **Step 1: 运行所有测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/ -v --tb=short
```

Expected: All tests PASS (Phase 1 的 13 个 + Phase 2 的 ~15 个)

- [ ] **Step 2: 启动应用验证**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m app.main &
sleep 3

# 验证首页
curl -s http://127.0.0.1:8765/ | grep "每日生产记录"

# 验证导入页面
curl -s http://127.0.0.1:8765/history-import | grep "历史记录导入"

# 验证导入 API
curl -s http://127.0.0.1:8765/api/import/batches

kill %1
```

- [ ] **Step 3: 最终提交**

```bash
git add .
git commit -m "chore: Phase 2 complete - history import with staging and knowledge extraction"
```
