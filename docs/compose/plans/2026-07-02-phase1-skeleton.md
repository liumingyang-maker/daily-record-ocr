# Phase 1: 项目骨架 + 本地 Web 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 FastAPI 项目骨架，实现 SQLite 数据库初始化、图片上传、任务列表显示，用户可通过浏览器访问本地 Web 页面。

**Architecture:** 分层架构（Interface/Application/Domain/Infrastructure/Config），FastAPI + Jinja2 模板 + SQLAlchemy ORM + SQLite。所有配置使用 YAML，环境变量使用 .env。

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, SQLAlchemy, SQLite, python-multipart, PyYAML, python-dotenv, uvicorn

## Global Constraints

- Python 3.11+（开发机 3.14 兼容）
- SQLite 数据库文件位于 `data/app.sqlite3`
- 上传图片存储在 `data/storage/raw_images/`
- 模板坐标使用 YAML 配置，不硬编码
- 所有模块必须独立，不允许单文件包含所有逻辑
- 使用分层架构：interfaces / application / domain / infrastructure / configs
- 每个提交必须可独立运行

---

### Task 1: 项目目录结构与依赖配置

**Covers:** [S3, S4, S13]

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/settings.py`
- Create: `app/logging_config.py`
- Create: `app/interfaces/__init__.py`
- Create: `app/application/__init__.py`
- Create: `app/domain/__init__.py`
- Create: `app/infrastructure/__init__.py`
- Create: `app/configs/__init__.py`
- Create: `app/tests/__init__.py`
- Create: `data/storage/raw_images/.gitkeep`
- Create: `data/storage/corrected_images/.gitkeep`
- Create: `data/storage/record_crops/.gitkeep`
- Create: `data/storage/cell_crops/.gitkeep`
- Create: `data/storage/history_imports/.gitkeep`
- Create: `data/storage/exports/.gitkeep`
- Create: `data/storage/debug/.gitkeep`
- Create: `data/backups/.gitkeep`
- Create: `models/paddleocr/.gitkeep`
- Create: `scripts/__init__.py`

**Interfaces:**
- Produces: 项目骨架目录结构，所有后续任务依赖此结构

- [ ] **Step 1: 创建项目目录结构**

```bash
cd /home/brian/Desktop/daily_record_ocr
mkdir -p app/interfaces/templates app/interfaces/static
mkdir -p app/application app/domain app/infrastructure/database
mkdir -p app/infrastructure/image app/infrastructure/ocr
mkdir -p app/infrastructure/vision app/infrastructure/history_import
mkdir -p app/infrastructure/excel app/infrastructure/storage
mkdir -p app/configs app/tests
mkdir -p data/storage/{raw_images,corrected_images,record_crops,cell_crops,history_imports,exports,debug}
mkdir -p data/backups models/paddleocr scripts installer launcher
touch app/__init__.py app/interfaces/__init__.py app/application/__init__.py
touch app/domain/__init__.py app/infrastructure/__init__.py app/configs/__init__.py
touch app/tests/__init__.py app/infrastructure/database/__init__.py
touch app/infrastructure/image/__init__.py app/infrastructure/ocr/__init__.py
touch app/infrastructure/vision/__init__.py app/infrastructure/history_import/__init__.py
touch app/infrastructure/excel/__init__.py app/infrastructure/storage/__init__.py
touch scripts/__init__.py
touch data/storage/raw_images/.gitkeep data/storage/corrected_images/.gitkeep
touch data/storage/record_crops/.gitkeep data/storage/cell_crops/.gitkeep
touch data/storage/history_imports/.gitkeep data/storage/exports/.gitkeep
touch data/storage/debug/.gitkeep data/backups/.gitkeep
touch models/paddleocr/.gitkeep
```

- [ ] **Step 2: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "daily-record-ocr"
version = "0.1.0"
description = "每日生产记录智能识别系统"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "jinja2>=3.1.2",
    "python-multipart>=0.0.6",
    "sqlalchemy>=2.0.23",
    "alembic>=1.13.0",
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
    "loguru>=0.7.2",
    "openpyxl>=3.1.2",
    "httpx>=0.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.23.0",
]
ocr = [
    "paddleocr>=2.7.0",
    "paddlepaddle>=2.5.0",
]
vision = [
    "opencv-python>=4.8.0",
]

[tool.pytest.ini_options]
testpaths = ["app/tests"]
asyncio_mode = "auto"
```

- [ ] **Step 3: 创建 requirements.txt**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
jinja2>=3.1.2
python-multipart>=0.0.6
sqlalchemy>=2.0.23
alembic>=1.13.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
loguru>=0.7.2
openpyxl>=3.1.2
httpx>=0.25.0
pytest>=7.4.3
pytest-asyncio>=0.23.0
```

- [ ] **Step 4: 创建 .env.example**

```
# 每日生产记录智能识别系统 - 环境变量配置
APP_HOST=127.0.0.1
APP_PORT=8765
DATABASE_URL=sqlite:///data/app.sqlite3
MIMO_API_KEY=
MIMO_MODEL=mimo-v2.5
LOG_LEVEL=INFO
```

- [ ] **Step 5: 创建 .gitignore**

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.env
data/app.sqlite3
data/storage/
data/backups/
*.sqlite3
.venv/
venv/
.idea/
.vscode/
```

- [ ] **Step 6: 创建 app/settings.py**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = DATA_DIR / "storage"
CONFIGS_DIR = BASE_DIR / "app" / "configs"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.sqlite3'}")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8765"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# MiMo
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5")

# Storage paths
RAW_IMAGES_DIR = STORAGE_DIR / "raw_images"
CORRECTED_IMAGES_DIR = STORAGE_DIR / "corrected_images"
RECORD_CROPS_DIR = STORAGE_DIR / "record_crops"
CELL_CROPS_DIR = STORAGE_DIR / "cell_crops"
HISTORY_IMPORTS_DIR = STORAGE_DIR / "history_imports"
EXPORTS_DIR = STORAGE_DIR / "exports"
DEBUG_DIR = STORAGE_DIR / "debug"
BACKUPS_DIR = DATA_DIR / "backups"
```

- [ ] **Step 7: 创建 app/logging_config.py**

```python
import sys
from loguru import logger
from app.settings import LOG_LEVEL

logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}")
logger.add("logs/app.log", rotation="10 MB", retention="30 days", level="DEBUG")
```

- [ ] **Step 8: 安装依赖并验证**

```bash
cd /home/brian/Desktop/daily_record_ocr
pip install -r requirements.txt
python -c "import fastapi; import sqlalchemy; import yaml; print('Dependencies OK')"
```

- [ ] **Step 9: 初始化 git 仓库并提交**

```bash
cd /home/brian/Desktop/daily_record_ocr
git init
git add .
git commit -m "feat: project skeleton with directory structure and dependencies"
```

---

### Task 2: SQLAlchemy 数据库模型（基础表）

**Covers:** [S6, S13]

**Files:**
- Create: `app/infrastructure/database/base.py`
- Create: `app/infrastructure/database/session.py`
- Create: `app/infrastructure/database/models.py`
- Create: `scripts/init_db.py`
- Create: `app/tests/test_database.py`

**Interfaces:**
- Produces: `get_session()` 异步上下文管理器，供所有 repository 使用
- Produces: `Base` 声明基类，供所有模型继承
- Produces: `init_db()` 函数，创建所有表

- [ ] **Step 1: 创建数据库基础配置**

```python
# app/infrastructure/database/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

```python
# app/infrastructure/database/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 2: 创建数据库模型（Phase 1 核心表）**

```python
# app/infrastructure/database/models.py
import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base

class RecognitionJob(Base):
    __tablename__ = "recognition_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_no = Column(String(50), unique=True, nullable=False)
    source_image_path = Column(String(500))
    corrected_image_path = Column(String(500))
    status = Column(String(20), default="UPLOADED")  # UPLOADED/PREPROCESSING/PREPROCESSED/RECOGNIZING/NEED_REVIEW/CONFIRMED/EXPORTED/FAILED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    error_message = Column(Text)
    ocr_engine = Column(String(50))
    mimo_used = Column(Boolean, default=False)
    mimo_mode = Column(String(30))
    export_path = Column(String(500))

    records = relationship("ProductionRecord", back_populates="job")


class ProductionRecord(Base):
    __tablename__ = "production_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("recognition_jobs.id"), nullable=False)
    record_index = Column(Integer)
    record_crop_path = Column(String(500))
    time_raw = Column(String(100))
    time_value = Column(String(50))
    customer_queue_raw = Column(String(200))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    color_raw = Column(String(100))
    color_standard = Column(String(100))
    date_batch_no_raw = Column(String(100))
    remark_raw = Column(Text)
    review_status = Column(String(20), default="PENDING")  # PENDING/REVIEWING/CONFIRMED/REJECTED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed_at = Column(DateTime)

    job = relationship("RecognitionJob", back_populates="records")
    material_items = relationship("RecordMaterialItem", back_populates="record")
    machine_params = relationship("RecordMachineParams", back_populates="record", uselist=False)
    temperatures = relationship("RecordTemperatures", back_populates="record", uselist=False)
    field_results = relationship("FieldRecognitionResult", back_populates="record")


class RecordMaterialItem(Base):
    __tablename__ = "record_material_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("production_records.id"), nullable=False)
    seq = Column(Integer)
    material_name_raw = Column(String(200))
    material_id = Column(Integer, ForeignKey("materials.id"))
    material_name_standard = Column(String(200))
    usage_raw = Column(String(100))
    usage_value = Column(Float)
    unit_raw = Column(String(50))
    unit_standard = Column(String(20))
    base_quantity_kg = Column(Float)
    confidence = Column(Float)
    source = Column(String(50))
    is_manual_corrected = Column(Boolean, default=False)

    record = relationship("ProductionRecord", back_populates="material_items")


class RecordMachineParams(Base):
    __tablename__ = "record_machine_params"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("production_records.id"), nullable=False)
    main_speed_raw = Column(String(50))
    main_speed_value = Column(Float)
    feeder_speed_raw = Column(String(50))
    feeder_speed_value = Column(Float)
    side_feeder_fiber_raw = Column(String(50))
    side_feeder_fiber_value = Column(Float)
    main_current_raw = Column(String(50))
    main_current_value = Column(Float)
    vacuum_raw = Column(String(50))
    vacuum_value = Column(Float)
    material_temperature_raw = Column(String(50))
    material_temperature_value = Column(Float)

    record = relationship("ProductionRecord", back_populates="machine_params")


class RecordTemperatures(Base):
    __tablename__ = "record_temperatures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("production_records.id"), nullable=False)
    zone_1_raw = Column(String(50))
    zone_1_value = Column(Float)
    zone_2_raw = Column(String(50))
    zone_2_value = Column(Float)
    zone_3_raw = Column(String(50))
    zone_3_value = Column(Float)
    zone_4_raw = Column(String(50))
    zone_4_value = Column(Float)
    zone_5_raw = Column(String(50))
    zone_5_value = Column(Float)
    zone_6_raw = Column(String(50))
    zone_6_value = Column(Float)
    zone_7_raw = Column(String(50))
    zone_7_value = Column(Float)
    zone_8_raw = Column(String(50))
    zone_8_value = Column(Float)
    zone_9_raw = Column(String(50))
    zone_9_value = Column(Float)
    zone_10_raw = Column(String(50))
    zone_10_value = Column(Float)
    head_temperature_raw = Column(String(50))
    head_temperature_value = Column(Float)

    record = relationship("ProductionRecord", back_populates="temperatures")


class FieldRecognitionResult(Base):
    __tablename__ = "field_recognition_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("recognition_jobs.id"), nullable=False)
    record_id = Column(Integer, ForeignKey("production_records.id"), nullable=False)
    field_key = Column(String(100))
    field_label = Column(String(100))
    cell_crop_path = Column(String(500))
    ocr_raw_text = Column(String(500))
    ocr_confidence = Column(Float)
    mimo_raw_text = Column(String(500))
    mimo_confidence = Column(Float)
    history_suggested_value = Column(String(500))
    history_confidence = Column(Float)
    final_value = Column(String(500))
    final_confidence = Column(Float)
    source = Column(String(100))
    need_review = Column(Boolean, default=False)
    manual_value = Column(String(500))
    manual_corrected = Column(Boolean, default=False)
    reason = Column(Text)
    warnings_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    record = relationship("ProductionRecord", back_populates="field_results")
    candidates = relationship("FieldCandidate", back_populates="field_result")


class FieldCandidate(Base):
    __tablename__ = "field_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_result_id = Column(Integer, ForeignKey("field_recognition_results.id"), nullable=False)
    candidate_value = Column(String(500))
    source = Column(String(50))
    confidence = Column(Float)
    reason = Column(Text)
    rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    field_result = relationship("FieldRecognitionResult", back_populates="candidates")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_code = Column(String(100))
    customer_name = Column(String(200))
    aliases_json = Column(JSON)
    status = Column(String(20), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_code = Column(String(100))
    product_name = Column(String(200))
    aliases_json = Column(JSON)
    default_color = Column(String(100))
    status = Column(String(20), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(100))
    standard_name = Column(String(200))
    category = Column(String(100))
    aliases_json = Column(JSON)
    common_ocr_errors_json = Column(JSON)
    unit_default = Column(String(20))
    status = Column(String(20), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class MaterialAlias(Base):
    __tablename__ = "material_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    alias = Column(String(200))
    alias_type = Column(String(30))  # MANUAL_ALIAS/HISTORY_ALIAS/OCR_ERROR/IMPORT_VARIANT
    source = Column(String(50))
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Formula(Base):
    __tablename__ = "formulas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    color = Column(String(100))
    formula_name = Column(String(200))
    formula_fingerprint = Column(String(500))
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    status = Column(String(20), default="ACTIVE")
    created_from_record_id = Column(Integer)
    created_from_import_batch_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class FormulaItem(Base):
    __tablename__ = "formula_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    formula_id = Column(Integer, ForeignKey("formulas.id"), nullable=False)
    seq = Column(Integer)
    material_id = Column(Integer, ForeignKey("materials.id"))
    usage_value = Column(Float)
    unit_raw = Column(String(50))
    unit_standard = Column(String(20))
    base_quantity_kg = Column(Float)
    tolerance_percent = Column(Float)
    tolerance_absolute = Column(Float)


class ManualCorrectionLog(Base):
    __tablename__ = "manual_correction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("production_records.id"))
    field_key = Column(String(100))
    old_value = Column(String(500))
    new_value = Column(String(500))
    operator = Column(String(100))
    correction_type = Column(String(30))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_no = Column(String(50), unique=True)
    source_file_path = Column(String(500))
    source_file_name = Column(String(200))
    file_hash = Column(String(100))
    import_profile = Column(String(100))
    status = Column(String(20), default="UPLOADED")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed_at = Column(DateTime)
    total_rows = Column(Integer)
    valid_rows = Column(Integer)
    invalid_rows = Column(Integer)
    error_message = Column(Text)


class ImportStagingRecord(Base):
    __tablename__ = "import_staging_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    source_sheet = Column(String(100))
    source_row_start = Column(Integer)
    record_index = Column(Integer)
    raw_payload_json = Column(JSON)
    normalized_payload_json = Column(JSON)
    validation_errors_json = Column(JSON)
    is_valid = Column(Boolean, default=True)
    is_selected = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ImportStagingMaterialItem(Base):
    __tablename__ = "import_staging_material_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    staging_record_id = Column(Integer, ForeignKey("import_staging_records.id"), nullable=False)
    seq = Column(Integer)
    material_name_raw = Column(String(200))
    material_name_clean = Column(String(200))
    usage_raw = Column(String(100))
    usage_value = Column(Float)
    unit_raw = Column(String(50))
    unit_standard = Column(String(20))
    base_quantity_kg = Column(Float)
    validation_status = Column(String(20))


class ImportStagingWarning(Base):
    __tablename__ = "import_staging_warnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"))
    staging_record_id = Column(Integer, ForeignKey("import_staging_records.id"))
    level = Column(String(20))  # INFO/WARNING/ERROR
    field_key = Column(String(100))
    message = Column(Text)
    suggested_action = Column(Text)


class MimoRequestLog(Base):
    __tablename__ = "mimo_request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("recognition_jobs.id"))
    record_id = Column(Integer)
    request_type = Column(String(50))
    model = Column(String(50))
    prompt_version = Column(String(50))
    image_hash = Column(String(100))
    request_payload_hash = Column(String(100))
    response_json = Column(JSON)
    success = Column(Boolean)
    error_message = Column(Text)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MimoCache(Base):
    __tablename__ = "mimo_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_hash = Column(String(100))
    prompt_version = Column(String(50))
    model = Column(String(50))
    response_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 3: 创建数据库初始化脚本**

```python
# scripts/init_db.py
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pathlib import Path
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine
from app.infrastructure.database.models import *  # noqa: ensure all models loaded

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
```

- [ ] **Step 4: 编写数据库测试**

```python
# app/tests/test_database.py
import pytest
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import RecognitionJob, Customer, Material

def test_create_tables():
    Base.metadata.create_all(bind=engine)
    assert "recognition_jobs" in Base.metadata.tables
    assert "customers" in Base.metadata.tables
    assert "materials" in Base.metadata.tables

def test_create_recognition_job():
    with get_session() as session:
        job = RecognitionJob(job_no="TEST-001", status="UPLOADED")
        session.add(job)
        session.flush()
        assert job.id is not None

def test_create_customer():
    with get_session() as session:
        customer = Customer(customer_code="C001", customer_name="Test Customer")
        session.add(customer)
        session.flush()
        assert customer.id is not None
```

- [ ] **Step 5: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m pytest app/tests/test_database.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: 初始化数据库**

```bash
cd /home/brian/Desktop/daily_record_ocr
python scripts/init_db.py
```

Expected: "Database initialized successfully."

- [ ] **Step 7: 提交**

```bash
git add app/infrastructure/database/ scripts/init_db.py app/tests/test_database.py
git commit -m "feat: SQLAlchemy models and database initialization"
```

---

### Task 3: FastAPI 主应用与基础路由

**Covers:** [S4, S12]

**Files:**
- Create: `app/main.py`
- Create: `app/interfaces/web_routes.py`
- Create: `app/interfaces/api_routes.py`
- Create: `app/tests/test_app.py`

**Interfaces:**
- Produces: FastAPI app 实例
- Produces: `GET /` 首页路由
- Produces: `GET /api/health` 健康检查

- [ ] **Step 1: 创建 FastAPI 主应用**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.interfaces.web_routes import router as web_router
from app.interfaces.api_routes import router as api_router

app = FastAPI(title="每日生产记录智能识别系统", version="0.1.0")

# Static files
static_dir = Path(__file__).parent / "interfaces" / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path(__file__).parent / "interfaces" / "templates"

# Routers
app.include_router(web_router)
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup():
    from app.infrastructure.database.base import Base
    from app.infrastructure.database.session import engine
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    from app.settings import APP_HOST, APP_PORT
    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=True)
```

- [ ] **Step 2: 创建 Web 路由**

```python
# app/interfaces/web_routes.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "每日生产记录智能识别系统"})
```

- [ ] **Step 3: 创建 API 路由**

```python
# app/interfaces/api_routes.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 4: 创建首页模板**

```html
<!-- app/interfaces/templates/base.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="/static/app.css">
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="/" class="brand">每日生产记录智能识别系统</a>
            <div class="nav-links">
                <a href="/">首页</a>
                <a href="/jobs">识别任务</a>
                <a href="/history-import">历史导入</a>
                <a href="/materials">物料库</a>
                <a href="/customers">客户库</a>
            </div>
        </div>
    </nav>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    <script src="/static/app.js"></script>
</body>
</html>
```

```html
<!-- app/interfaces/templates/index.html -->
{% extends "base.html" %}
{% block content %}
<h1>系统首页</h1>
<div class="dashboard">
    <div class="card">
        <h3>识别任务</h3>
        <p>上传手写生产记录图片，自动识别并生成结构化数据</p>
        <a href="/jobs" class="btn">查看任务列表</a>
    </div>
    <div class="card">
        <h3>历史导入</h3>
        <p>导入电子版历史生产记录，建立知识库</p>
        <a href="/history-import" class="btn">导入历史数据</a>
    </div>
    <div class="card">
        <h3>物料库</h3>
        <p>管理物料名称、别名、单位</p>
        <a href="/materials" class="btn">查看物料库</a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: 创建基础 CSS**

```css
/* app/interfaces/static/app.css */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; }
.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.navbar { background: #2563eb; color: white; padding: 12px 0; }
.navbar .container { display: flex; justify-content: space-between; align-items: center; }
.navbar .brand { color: white; text-decoration: none; font-size: 18px; font-weight: bold; }
.nav-links a { color: rgba(255,255,255,0.9); text-decoration: none; margin-left: 20px; }
.nav-links a:hover { color: white; }
h1 { margin: 20px 0; }
.dashboard { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
.card { background: white; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.card h3 { margin-bottom: 8px; }
.card p { color: #666; margin-bottom: 16px; }
.btn { display: inline-block; background: #2563eb; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; }
.btn:hover { background: #1d4ed8; }
.btn-success { background: #16a34a; }
.btn-success:hover { background: #15803d; }
.btn-danger { background: #dc2626; }
.btn-danger:hover { background: #b91c1c; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #f8fafc; font-weight: 600; }
.status-uploaded { color: #2563eb; }
.status-need-review { color: #d97706; }
.status-confirmed { color: #16a34a; }
.status-failed { color: #dc2626; }
```

- [ ] **Step 6: 创建基础 JS**

```javascript
// app/interfaces/static/app.js
console.log("Daily Record OCR System loaded");
```

- [ ] **Step 7: 编写应用测试**

```python
# app/tests/test_app.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "每日生产记录" in response.text
```

- [ ] **Step 8: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m pytest app/tests/test_app.py -v
```

Expected: 2 tests PASS

- [ ] **Step 9: 启动服务验证**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m app.main &
sleep 2
curl -s http://127.0.0.1:8765/api/health
curl -s http://127.0.0.1:8765/ | head -5
kill %1
```

Expected: health check returns JSON, index returns HTML

- [ ] **Step 10: 提交**

```bash
git add app/main.py app/interfaces/ app/tests/test_app.py
git commit -m "feat: FastAPI app with web routes and templates"
```

---

### Task 4: 图片上传与任务管理

**Covers:** [S5, S12]

**Files:**
- Create: `app/infrastructure/storage/file_storage.py`
- Create: `app/infrastructure/storage/path_manager.py`
- Create: `app/application/upload_service.py`
- Modify: `app/interfaces/api_routes.py`
- Modify: `app/interfaces/web_routes.py`
- Create: `app/interfaces/templates/jobs.html`
- Create: `app/tests/test_upload.py`

**Interfaces:**
- Produces: `FileStorage.save_image(file) -> (path, filename)` 保存上传图片
- Produces: `UploadService.create_job(file) -> RecognitionJob` 创建识别任务
- Produces: `POST /api/jobs/upload` 上传接口
- Produces: `GET /api/jobs` 任务列表接口
- Produces: `GET /jobs` 任务列表页面

- [ ] **Step 1: 创建文件存储模块**

```python
# app/infrastructure/storage/path_manager.py
import hashlib
import datetime
from pathlib import Path
from app.settings import RAW_IMAGES_DIR, STORAGE_DIR

def generate_job_no() -> str:
    now = datetime.datetime.now()
    return now.strftime("JOB%Y%m%d%H%M%S")

def get_raw_image_path(filename: str) -> Path:
    today = datetime.date.today().strftime("%Y%m%d")
    target_dir = RAW_IMAGES_DIR / today
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / filename

def calculate_file_hash(file_path: Path) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```

```python
# app/infrastructure/storage/file_storage.py
import shutil
from pathlib import Path
from fastapi import UploadFile
from app.infrastructure.storage.path_manager import get_raw_image_path

class FileStorage:
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

    async def save_image(self, file: UploadFile) -> tuple[Path, str]:
        ext = Path(file.filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}")

        target_path = get_raw_image_path(file.filename)
        with open(target_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return target_path, file.filename
```

- [ ] **Step 2: 创建上传服务**

```python
# app/application/upload_service.py
from pathlib import Path
from fastapi import UploadFile
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import RecognitionJob
from app.infrastructure.storage.file_storage import FileStorage
from app.infrastructure.storage.path_manager import generate_job_no, calculate_file_hash

class UploadService:
    def __init__(self):
        self.file_storage = FileStorage()

    async def create_job(self, file: UploadFile) -> RecognitionJob:
        # Save file
        file_path, original_name = await self.file_storage.save_image(file)
        file_hash = calculate_file_hash(file_path)

        # Create job
        with get_session() as session:
            job = RecognitionJob(
                job_no=generate_job_no(),
                source_image_path=str(file_path),
                status="UPLOADED",
            )
            session.add(job)
            session.flush()
            job_id = job.id

        # Return job (re-fetch to get all fields)
        with get_session() as session:
            return session.query(RecognitionJob).get(job_id)

    def list_jobs(self, limit: int = 50) -> list[RecognitionJob]:
        with get_session() as session:
            return session.query(RecognitionJob).order_by(RecognitionJob.created_at.desc()).limit(limit).all()

    def get_job(self, job_id: int) -> RecognitionJob | None:
        with get_session() as session:
            return session.query(RecognitionJob).get(job_id)
```

- [ ] **Step 3: 更新 API 路由（添加上传和任务列表）**

```python
# app/interfaces/api_routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.application.upload_service import UploadService

router = APIRouter()
upload_service = UploadService()

@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

@router.post("/jobs/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        job = await upload_service.create_job(file)
        return {"job_id": job.id, "job_no": job.job_no, "status": job.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs")
async def list_jobs(limit: int = 50):
    jobs = upload_service.list_jobs(limit)
    return [
        {
            "id": j.id,
            "job_no": j.job_no,
            "status": j.status,
            "source_image_path": j.source_image_path,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]

@router.get("/jobs/{job_id}")
async def get_job(job_id: int):
    job = upload_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "job_no": job.job_no,
        "status": job.status,
        "source_image_path": job.source_image_path,
        "corrected_image_path": job.corrected_image_path,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
```

- [ ] **Step 4: 更新 Web 路由（添加任务列表页面）**

```python
# app/interfaces/web_routes.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.application.upload_service import UploadService

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
upload_service = UploadService()

@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "每日生产记录智能识别系统"})

@router.get("/jobs")
async def jobs_page(request: Request):
    jobs = upload_service.list_jobs()
    return templates.TemplateResponse("jobs.html", {"request": request, "title": "识别任务", "jobs": jobs})
```

- [ ] **Step 5: 创建任务列表模板**

```html
<!-- app/interfaces/templates/jobs.html -->
{% extends "base.html" %}
{% block content %}
<div class="page-header">
    <h1>识别任务</h1>
    <form id="upload-form" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*" required>
        <button type="submit" class="btn btn-success">上传图片</button>
    </form>
</div>

<table>
    <thead>
        <tr>
            <th>任务编号</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
        </tr>
    </thead>
    <tbody>
        {% for job in jobs %}
        <tr>
            <td>{{ job.job_no }}</td>
            <td><span class="status-{{ job.status.lower().replace('_', '-') }}">{{ job.status }}</span></td>
            <td>{{ job.created_at.strftime('%Y-%m-%d %H:%M') if job.created_at else '-' }}</td>
            <td><a href="/jobs/{{ job.id }}" class="btn">查看</a></td>
        </tr>
        {% endfor %}
        {% if not jobs %}
        <tr><td colspan="4" style="text-align:center; color:#999;">暂无任务，请上传图片</td></tr>
        {% endif %}
    </tbody>
</table>

<script>
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    try {
        const resp = await fetch('/api/jobs/upload', { method: 'POST', body: formData });
        if (resp.ok) {
            window.location.reload();
        } else {
            const err = await resp.json();
            alert('上传失败: ' + (err.detail || '未知错误'));
        }
    } catch (err) {
        alert('上传失败: ' + err.message);
    }
});
</script>

<style>
.page-header { display: flex; justify-content: space-between; align-items: center; margin: 20px 0; }
.page-header h1 { margin: 0; }
#upload-form { display: flex; gap: 10px; align-items: center; }
#upload-form input[type="file"] { padding: 6px; }
</style>
{% endblock %}
```

- [ ] **Step 6: 编写上传测试**

```python
# app/tests/test_upload.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)

def test_upload_image():
    # Create a fake image file
    fake_image = io.BytesIO(b"fake image content")
    fake_image.name = "test_image.jpg"

    response = client.post(
        "/api/jobs/upload",
        files={"file": ("test_image.jpg", fake_image, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "job_no" in data
    assert data["status"] == "UPLOADED"

def test_list_jobs():
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_upload_unsupported_format():
    fake_file = io.BytesIO(b"not an image")
    fake_file.name = "test.txt"

    response = client.post(
        "/api/jobs/upload",
        files={"file": ("test.txt", fake_file, "text/plain")}
    )
    assert response.status_code == 400

def test_jobs_page():
    response = client.get("/jobs")
    assert response.status_code == 200
    assert "识别任务" in response.text
```

- [ ] **Step 7: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m pytest app/tests/test_upload.py -v
```

Expected: 4 tests PASS

- [ ] **Step 8: 提交**

```bash
git add app/infrastructure/storage/ app/application/upload_service.py app/interfaces/ app/tests/test_upload.py
git commit -m "feat: image upload and job management"
```

---

### Task 5: 任务详情页面

**Covers:** [S12]

**Files:**
- Create: `app/interfaces/templates/job_detail.html`
- Modify: `app/interfaces/web_routes.py`

**Interfaces:**
- Produces: `GET /jobs/{job_id}` 任务详情页面

- [ ] **Step 1: 添加任务详情路由**

```python
# 在 app/interfaces/web_routes.py 中添加
@router.get("/jobs/{job_id}")
async def job_detail_page(request: Request, job_id: int):
    job = upload_service.get_job(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "title": f"任务详情 - {job.job_no}",
        "job": job,
    })
```

- [ ] **Step 2: 创建任务详情模板**

```html
<!-- app/interfaces/templates/job_detail.html -->
{% extends "base.html" %}
{% block content %}
<div class="page-header">
    <h1>任务详情: {{ job.job_no }}</h1>
    <a href="/jobs" class="btn">返回列表</a>
</div>

<div class="detail-grid">
    <div class="detail-card">
        <h3>基本信息</h3>
        <table>
            <tr><td>任务编号</td><td>{{ job.job_no }}</td></tr>
            <tr><td>状态</td><td><span class="status-{{ job.status.lower().replace('_', '-') }}">{{ job.status }}</span></td></tr>
            <tr><td>创建时间</td><td>{{ job.created_at.strftime('%Y-%m-%d %H:%M:%S') if job.created_at else '-' }}</td></tr>
            <tr><td>OCR引擎</td><td>{{ job.ocr_engine or '-' }}</td></tr>
            <tr><td>MiMo使用</td><td>{{ '是' if job.mimo_used else '否' }}</td></tr>
            {% if job.error_message %}
            <tr><td>错误信息</td><td style="color:red">{{ job.error_message }}</td></tr>
            {% endif %}
        </table>
    </div>

    <div class="detail-card">
        <h3>原始图片</h3>
        {% if job.source_image_path %}
        <img src="/static/{{ job.source_image_path }}" alt="原始图片" style="max-width:100%; border:1px solid #ddd; border-radius:4px;">
        {% else %}
        <p style="color:#999">无图片</p>
        {% endif %}
    </div>
</div>

<style>
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
.detail-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.detail-card h3 { margin-bottom: 12px; }
.detail-card table td:first-child { font-weight: 600; padding-right: 16px; }
</style>
{% endblock %}
```

- [ ] **Step 3: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m pytest app/tests/ -v
```

Expected: All tests PASS

- [ ] **Step 4: 提交**

```bash
git add app/interfaces/templates/job_detail.html app/interfaces/web_routes.py
git commit -m "feat: job detail page"
```

---

### Task 6: 配置系统与 YAML 加载

**Covers:** [S13]

**Files:**
- Create: `app/configs/app.yaml`
- Create: `app/configs/ocr.yaml`
- Create: `app/configs/mimo.yaml`
- Create: `app/configs/rules.yaml`
- Create: `app/configs/unit_rules.yaml`
- Create: `app/configs/template_daily_record_v1.yaml`
- Create: `app/configs/export_config.yaml`

**Interfaces:**
- Produces: `load_config(name) -> dict` 配置加载函数

- [ ] **Step 1: 创建配置加载工具**

```python
# app/configs/__init__.py
import yaml
from pathlib import Path
from functools import lru_cache

CONFIGS_DIR = Path(__file__).parent

@lru_cache(maxsize=32)
def load_config(name: str) -> dict:
    config_path = CONFIGS_DIR / f"{name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
```

- [ ] **Step 2: 创建各配置文件（使用方案中的示例值）**

```yaml
# app/configs/app.yaml
app:
  name: "每日生产记录智能识别系统"
  version: "0.1.0"
  host: "127.0.0.1"
  port: 8765
  debug: false
```

```yaml
# app/configs/ocr.yaml
ocr:
  engine: "paddleocr"
  model: "PP-OCRv6-medium"
  use_gpu: false
  lang: "ch"
  confidence_threshold: 0.6
```

```yaml
# app/configs/mimo.yaml
mimo:
  enabled: true
  mode: "record_level"
  model: "mimo-v2.5"
  api_key_env: "MIMO_API_KEY"
  timeout_seconds: 60
  max_retry: 2
  cache_enabled: true
  prompt_version: "daily_record_v1_202607"
  send_history_candidates: true
  max_history_candidates: 10
  max_material_candidates: 30
```

```yaml
# app/configs/rules.yaml
fields:
  time:
    type: date
    required: true
  customer_queue:
    type: text
    required: false
  material_name:
    type: material
    required: true
  usage:
    type: quantity
    required: true
    min: 0
    max: 100000
  main_speed:
    type: number
    required: false
    min: 0
    max: 3000
  temperature:
    type: number
    required: false
    min: 0
    max: 500

confidence:
  green: 0.95
  yellow: 0.80
  red: 0.80
```

```yaml
# app/configs/unit_rules.yaml
units:
  g:
    aliases: ["g", "克", "公克"]
    base: kg
    factor_to_base: 0.001
  kg:
    aliases: ["kg", "KG", "公斤", "千克"]
    base: kg
    factor_to_base: 1
  t:
    aliases: ["吨", "t", "T"]
    base: kg
    factor_to_base: 1000
  bag:
    aliases: ["包", "袋"]
    base: null
    factor_to_base: null
  bucket:
    aliases: ["桶"]
    base: null
    factor_to_base: null
  portion:
    aliases: ["份"]
    base: null
    factor_to_base: null
```

```yaml
# app/configs/template_daily_record_v1.yaml
template_name: daily_production_record_v1
canonical_size:
  width: 1800
  height: 2500

record_blocks:
  - key: record_1
    index: 1
    rect: [80, 210, 1700, 800]
  - key: record_2
    index: 2
    rect: [80, 850, 1700, 1440]
  - key: record_3
    index: 3
    rect: [80, 1490, 1700, 2080]

fields:
  time:
    label: 时间
    type: date
    roi_in_record: [0, 0, 230, 70]
    ocr_mode: text
    required: true
  customer_queue:
    label: 客户及排号
    type: text
    roi_in_record: [300, 0, 650, 70]
    ocr_mode: text
    required: false
  color:
    label: 颜色
    type: text
    roi_in_record: [720, 0, 980, 70]
    ocr_mode: text
    required: false
  date_batch_no:
    label: 日期牌号
    type: text
    roi_in_record: [1160, 0, 1620, 70]
    ocr_mode: text
    required: false

material_table:
  name_row_y: [80, 155]
  usage_row_y: [155, 230]
  columns:
    - seq: 1
      x: [0, 170]
    - seq: 2
      x: [170, 340]
    - seq: 3
      x: [340, 510]
    - seq: 4
      x: [510, 680]
    - seq: 5
      x: [680, 850]
    - seq: 6
      x: [850, 1020]
    - seq: 7
      x: [1020, 1190]
    - seq: 8
      x: [1190, 1360]

machine_fields:
  main_speed:
    label: 主机转速
    type: number
    roi_in_record: [0, 260, 160, 330]
  feeder_speed:
    label: 喂料转速
    type: number
    roi_in_record: [160, 260, 320, 330]
  side_feeder_fiber:
    label: 侧喂料加纤
    type: number
    roi_in_record: [320, 260, 500, 330]
  main_current:
    label: 主机电流
    type: number
    roi_in_record: [500, 260, 680, 330]
  vacuum:
    label: 真空度
    type: number
    roi_in_record: [680, 260, 850, 330]
  material_temperature:
    label: 物料温度
    type: number
    roi_in_record: [850, 260, 1030, 330]

temperature_fields:
  zone_1:
    label: 1区温度
    type: number
    roi_in_record: [0, 350, 120, 420]
  zone_2:
    label: 2区温度
    type: number
    roi_in_record: [120, 350, 240, 420]
  zone_3:
    label: 3区温度
    type: number
    roi_in_record: [240, 350, 360, 420]
  zone_4:
    label: 4区温度
    type: number
    roi_in_record: [360, 350, 480, 420]
  zone_5:
    label: 5区温度
    type: number
    roi_in_record: [480, 350, 600, 420]
  zone_6:
    label: 6区温度
    type: number
    roi_in_record: [600, 350, 720, 420]
  zone_7:
    label: 7区温度
    type: number
    roi_in_record: [720, 350, 840, 420]
  zone_8:
    label: 8区温度
    type: number
    roi_in_record: [840, 350, 960, 420]
  zone_9:
    label: 9区温度
    type: number
    roi_in_record: [960, 350, 1080, 420]
  zone_10:
    label: 10区温度
    type: number
    roi_in_record: [1080, 350, 1200, 420]
  head_temperature:
    label: 机头温度
    type: number
    roi_in_record: [1200, 350, 1340, 420]
```

```yaml
# app/configs/export_config.yaml
export:
  sheets:
    - name: "生产记录汇总"
      type: "summary"
    - name: "配方明细"
      type: "formula_detail"
    - name: "识别审查"
      type: "recognition_review"
    - name: "导入修正摘要"
      type: "import_summary"
  output_dir: "data/storage/exports"
```

- [ ] **Step 3: 编写配置加载测试**

```python
# app/tests/test_configs.py
import pytest
from app.configs import load_config

def test_load_app_config():
    config = load_config("app")
    assert config["app"]["name"] == "每日生产记录智能识别系统"

def test_load_unit_rules():
    config = load_config("unit_rules")
    assert "kg" in config["units"]
    assert config["units"]["kg"]["factor_to_base"] == 1

def test_load_template():
    config = load_config("template_daily_record_v1")
    assert len(config["record_blocks"]) == 3
    assert config["canonical_size"]["width"] == 1800

def test_load_nonexistent_config():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent")
```

- [ ] **Step 4: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m pytest app/tests/test_configs.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/configs/
git commit -m "feat: YAML configuration files and loader"
```

---

### Task 7: 完整测试套件运行与最终验证

**Covers:** [S12, S14]

**Files:**
- Verify all existing tests pass
- Verify application starts correctly

**Interfaces:**
- N/A (verification task)

- [ ] **Step 1: 运行所有测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m pytest app/tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 2: 启动应用并手动验证**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -m app.main &
sleep 3

# Verify health check
curl -s http://127.0.0.1:8765/api/health

# Verify index page
curl -s http://127.0.0.1:8765/ | grep "每日生产记录"

# Verify jobs page
curl -s http://127.0.0.1:8765/jobs | grep "识别任务"

# Upload a test image
echo "fake image" > /tmp/test.jpg
curl -s -F "file=@/tmp/test_image.jpg" http://127.0.0.1:8765/api/jobs/upload

# List jobs
curl -s http://127.0.0.1:8765/api/jobs

kill %1
```

- [ ] **Step 3: 检查数据库**

```bash
cd /home/brian/Desktop/daily_record_ocr
python -c "
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import RecognitionJob
with get_session() as s:
    jobs = s.query(RecognitionJob).all()
    print(f'Total jobs: {len(jobs)}')
    for j in jobs:
        print(f'  {j.job_no}: {j.status}')
"
```

- [ ] **Step 4: 最终提交**

```bash
git add .
git commit -m "chore: Phase 1 complete - project skeleton with FastAPI, SQLite, web UI, upload"
```
