# Phase 3: 图像校正 + 模板切格 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现图片预处理流程：图像校正（透视变换、旋转校正）→ 模板切格（按 YAML 配置切割 3 条记录区域）→ 字段小格子切割，为后续 OCR 识别做准备。

**Architecture:** Infrastructure 层的 image 模块负责所有 OpenCV 图像处理。使用 `app/configs/template_daily_record_v1.yaml` 中的坐标配置进行切割。校正后的图片和切片保存到对应 storage 目录。

**Tech Stack:** OpenCV (opencv-python), NumPy, YAML config

## Global Constraints

- 模板坐标使用 YAML 配置，不硬编码
- 标准尺寸 1800×2500，图片需先缩放到标准尺寸
- 每张图切 3 条记录区域（record_blocks）
- 每条记录区域再按字段 ROI 切分小格子
- 校正图片存 `data/storage/corrected_images/`
- 记录切片存 `data/storage/record_crops/`
- 字段切片存 `data/storage/cell_crops/`
- 依赖 Phase 1 的 RecognitionJob 模型和 Phase 2 的上传流程

---

### Task 1: 图像校正模块

**Covers:** [S5]

**Files:**
- Create: `app/infrastructure/image/__init__.py`
- Create: `app/infrastructure/image/preprocessor.py`
- Create: `app/tests/test_preprocessor.py`

**Interfaces:**
- Produces: `preprocess_image(image_path, job_id) -> Path` 校正图片，返回保存路径
- Produces: `resize_to_standard(image, target_size=(1800,2500)) -> ndarray` 缩放到标准尺寸
- Produces: `auto_rotate(image) -> ndarray` 自动旋转校正

- [ ] **Step 1: 创建图像校正模块**

```python
# app/infrastructure/image/preprocessor.py
import cv2
import numpy as np
from pathlib import Path
from app.settings import CORRECTED_IMAGES_DIR, DEBUG_DIR


def load_image(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img


def resize_to_standard(img: np.ndarray, target_size: tuple[int, int] = (1800, 2500)) -> np.ndarray:
    h, w = img.shape[:2]
    tw, th = target_size
    if (w, h) == (tw, th):
        return img
    return cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)


def auto_rotate(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    if h < w:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    return img


def enhance_contrast(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def preprocess_image(image_path: str | Path, job_id: int) -> Path:
    img = load_image(image_path)
    img = auto_rotate(img)
    img = enhance_contrast(img)
    img = resize_to_standard(img)

    CORRECTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CORRECTED_IMAGES_DIR / f"job{job_id}_corrected.jpg"
    cv2.imwrite(str(out_path), img)
    return out_path
```

- [ ] **Step 2: 编写测试**

```python
# app/tests/test_preprocessor.py
import cv2
import numpy as np
import pytest
from pathlib import Path

from app.infrastructure.image.preprocessor import (
    resize_to_standard,
    auto_rotate,
    enhance_contrast,
)


def test_resize_to_standard():
    img = np.zeros((2500, 1800, 3), dtype=np.uint8)
    result = resize_to_standard(img)
    assert result.shape == (2500, 1800, 3)


def test_resize_from_larger():
    img = np.zeros((3000, 2000, 3), dtype=np.uint8)
    result = resize_to_standard(img)
    assert result.shape == (2500, 1800, 3)


def test_auto_rotate_landscape():
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    result = auto_rotate(img)
    assert result.shape[0] > result.shape[1]


def test_auto_rotate_portrait():
    img = np.zeros((200, 100, 3), dtype=np.uint8)
    result = auto_rotate(img)
    assert result.shape[0] > result.shape[1]


def test_enhance_contrast():
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    result = enhance_contrast(img)
    assert result.shape == img.shape
```

- [ ] **Step 3: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_preprocessor.py -v
```

Expected: 5 tests PASS

- [ ] **Step 4: 提交**

```bash
git add app/infrastructure/image/ app/tests/test_preprocessor.py
git commit -m "feat: image preprocessor with rotate, resize, contrast enhancement"
```

---

### Task 2: 模板切格模块

**Covers:** [S5, S13]

**Files:**
- Create: `app/infrastructure/image/cropper.py`
- Create: `app/tests/test_cropper.py`

**Interfaces:**
- Consumes: `app/configs/template_daily_record_v1.yaml` 配置
- Produces: `crop_record_blocks(image, template_config) -> list[dict]` 切割 3 条记录区域
- Produces: `crop_field_cells(record_image, template_config, record_index) -> dict[str, Path]` 切割字段小格子

- [ ] **Step 1: 创建切格模块**

```python
# app/infrastructure/image/cropper.py
import cv2
import numpy as np
from pathlib import Path
from app.settings import RECORD_CROPS_DIR, CELL_CROPS_DIR


def crop_rect(img: np.ndarray, rect: list[int]) -> np.ndarray:
    x1, y1, x2, y2 = rect
    return img[y1:y2, x1:x2]


def crop_record_blocks(image: np.ndarray, template: dict, job_id: int) -> list[dict]:
    records = []
    for block in template.get("record_blocks", []):
        rect = block["rect"]
        crop = crop_rect(image, rect)
        records.append({
            "index": block["index"],
            "key": block["key"],
            "image": crop,
            "rect": rect,
        })
    return records


def save_record_crops(records: list[dict], job_id: int) -> list[dict]:
    RECORD_CROPS_DIR.mkdir(parents=True, exist_ok=True)
    for rec in records:
        out_path = RECORD_CROPS_DIR / f"job{job_id}_record{rec['index']}.jpg"
        cv2.imwrite(str(out_path), rec["image"])
        rec["crop_path"] = str(out_path)
    return records


def crop_field_cells(record_image: np.ndarray, template: dict, job_id: int, record_index: int) -> dict[str, str]:
    CELL_CROPS_DIR.mkdir(parents=True, exist_ok=True)
    result = {}

    fields = template.get("fields", {})
    for field_key, field_def in fields.items():
        roi = field_def.get("roi_in_record")
        if not roi:
            continue
        x1, y1, x2, y2 = roi
        cell = record_image[y1:y2, x1:x2]
        out_path = CELL_CROPS_DIR / f"job{job_id}_r{record_index}_{field_key}.jpg"
        cv2.imwrite(str(out_path), cell)
        result[field_key] = str(out_path)

    return result
```

- [ ] **Step 2: 编写测试**

```python
# app/tests/test_cropper.py
import cv2
import numpy as np
import pytest

from app.infrastructure.image.cropper import crop_rect, crop_record_blocks, crop_field_cells


def test_crop_rect():
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    img[10:30, 10:50] = 255
    crop = crop_rect(img, [10, 10, 50, 30])
    assert crop.shape == (20, 40, 3)
    assert crop[0, 0, 0] == 255


def test_crop_record_blocks():
    img = np.zeros((2500, 1800, 3), dtype=np.uint8)
    template = {
        "record_blocks": [
            {"key": "r1", "index": 1, "rect": [80, 210, 1700, 800]},
            {"key": "r2", "index": 2, "rect": [80, 850, 1700, 1440]},
            {"key": "r3", "index": 3, "rect": [80, 1490, 1700, 2080]},
        ]
    }
    records = crop_record_blocks(img, template, job_id=1)
    assert len(records) == 3
    assert records[0]["image"].shape == (590, 1620, 3)
    assert records[1]["index"] == 2


def test_crop_field_cells():
    img = np.zeros((590, 1620, 3), dtype=np.uint8)
    template = {
        "fields": {
            "time": {"roi_in_record": [0, 0, 230, 70]},
            "customer": {"roi_in_record": [300, 0, 650, 70]},
        }
    }
    result = crop_field_cells(img, template, job_id=1, record_index=1)
    assert "time" in result
    assert "customer" in result
```

- [ ] **Step 3: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_cropper.py -v
```

Expected: 3 tests PASS

- [ ] **Step 4: 提交**

```bash
git add app/infrastructure/image/cropper.py app/tests/test_cropper.py
git commit -m "feat: template-based image cropping for records and fields"
```

---

### Task 3: 预处理服务整合

**Covers:** [S5, S4]

**Files:**
- Create: `app/application/preprocess_service.py`
- Create: `app/tests/test_preprocess_service.py`

**Interfaces:**
- Consumes: `preprocess_image`, `crop_record_blocks`, `crop_field_cells` from Tasks 1-2
- Consumes: `load_config("template_daily_record_v1")` from config
- Produces: `PreprocessService.process(job_id) -> dict` 完整预处理流程

- [ ] **Step 1: 创建预处理服务**

```python
# app/application/preprocess_service.py
from app.configs import load_config
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import RecognitionJob, ProductionRecord
from app.infrastructure.image.preprocessor import preprocess_image
from app.infrastructure.image.cropper import crop_record_blocks, save_record_crops, crop_field_cells


class PreprocessService:
    def __init__(self):
        self.template = load_config("template_daily_record_v1")

    def process(self, job_id: int) -> dict:
        with get_session() as session:
            job = session.query(RecognitionJob).get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            job.status = "PREPROCESSING"
            session.flush()
            source_path = job.source_image_path

        # 校正图片
        corrected_path = preprocess_image(source_path, job_id)

        # 读取校正后图片
        import cv2
        img = cv2.imread(str(corrected_path))

        # 切割记录区域
        records = crop_record_blocks(img, self.template, job_id)
        records = save_record_crops(records, job_id)

        # 切割字段小格子
        field_crops = {}
        for rec in records:
            cells = crop_field_cells(rec["image"], self.template, job_id, rec["index"])
            field_crops[rec["index"]] = cells

        # 更新数据库
        with get_session() as session:
            job = session.query(RecognitionJob).get(job_id)
            job.corrected_image_path = str(corrected_path)
            job.status = "PREPROCESSED"

            for rec in records:
                pr = ProductionRecord(
                    job_id=job_id,
                    record_index=rec["index"],
                    record_crop_path=rec.get("crop_path"),
                )
                session.add(pr)

        return {
            "job_id": job_id,
            "corrected_path": str(corrected_path),
            "records_count": len(records),
            "field_crops": field_crops,
        }
```

- [ ] **Step 2: 编写测试**

```python
# app/tests/test_preprocess_service.py
import cv2
import numpy as np
import pytest
from pathlib import Path

from app.application.preprocess_service import PreprocessService
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import RecognitionJob, ProductionRecord
from app.settings import RAW_IMAGES_DIR


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def sample_image(tmp_path):
    img = np.zeros((2500, 1800, 3), dtype=np.uint8)
    path = tmp_path / "test.jpg"
    cv2.imwrite(str(path), img)
    return path


@pytest.fixture
def job(sample_image):
    with get_session() as session:
        job = RecognitionJob(
            job_no="TEST-PREPROCESS-001",
            source_image_path=str(sample_image),
            status="UPLOADED",
        )
        session.add(job)
        session.flush()
        job_id = job.id
    return job_id


def test_process_creates_corrected_image(job):
    service = PreprocessService()
    result = service.process(job)
    assert Path(result["corrected_path"]).exists()
    assert result["records_count"] == 3


def test_process_creates_production_records(job):
    service = PreprocessService()
    service.process(job)
    with get_session() as session:
        records = session.query(ProductionRecord).filter_by(job_id=job).all()
        assert len(records) == 3


def test_process_updates_job_status(job):
    service = PreprocessService()
    service.process(job)
    with get_session() as session:
        j = session.query(RecognitionJob).get(job)
        assert j.status == "PREPROCESSED"
        assert j.corrected_image_path is not None
```

- [ ] **Step 3: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_preprocess_service.py -v
```

Expected: 3 tests PASS

- [ ] **Step 4: 运行全部测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/ -v
```

Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/application/preprocess_service.py app/tests/test_preprocess_service.py
git commit -m "feat: preprocess service integrating image correction and template cropping"
```

---

### Task 4: 预处理 API 端点

**Covers:** [S5, S12]

**Files:**
- Modify: `app/interfaces/api_routes.py` (add preprocess endpoint)
- Create: `app/tests/test_preprocess_api.py`

**Interfaces:**
- Consumes: `PreprocessService` from Task 3
- Produces: `POST /api/jobs/{job_id}/preprocess` 触发预处理

- [ ] **Step 1: 添加预处理 API**

在 `app/interfaces/api_routes.py` 中添加：

```python
from app.application.preprocess_service import PreprocessService
preprocess_service = PreprocessService()

@router.post("/jobs/{job_id}/preprocess")
async def preprocess_job(job_id: int):
    try:
        result = preprocess_service.process(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 2: 编写测试**

```python
# app/tests/test_preprocess_api.py
import cv2
import numpy as np
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import RecognitionJob

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _create_job_with_image() -> int:
    img = np.zeros((2500, 1800, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    resp = client.post(
        "/api/jobs/upload",
        files={"file": ("test.jpg", buf.tobytes(), "image/jpeg")},
    )
    return resp.json()["job_id"]


def test_preprocess_job():
    job_id = _create_job_with_image()
    resp = client.post(f"/api/jobs/{job_id}/preprocess")
    assert resp.status_code == 200
    data = resp.json()
    assert data["records_count"] == 3


def test_preprocess_not_found():
    resp = client.post("/api/jobs/99999/preprocess")
    assert resp.status_code == 404
```

- [ ] **Step 3: 运行测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_preprocess_api.py -v
```

Expected: 2 tests PASS

- [ ] **Step 4: 运行全部测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/ -v
```

Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/interfaces/api_routes.py app/tests/test_preprocess_api.py
git commit -m "feat: preprocess API endpoint for image correction and cropping"
```

---

### Task 5: Phase 3 完整验证

**Covers:** [S12, S14]

- [ ] **Step 1: 运行所有测试**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 2: 最终提交**

```bash
git add .
git commit -m "chore: Phase 3 complete - image preprocessing with OpenCV"
```
