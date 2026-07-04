# Phase 6: 候选融合 + 历史匹配 Implementation Plan

**Goal:** 实现多来源候选融合算法和历史配方匹配。每个字段综合 OCR、MiMo、历史匹配、物料字典等来源生成候选结果，按置信度排序，更新 field_candidates 表。

**Architecture:** Application 层的 fusion_service 负责融合逻辑。Domain 层的 matcher 负责物料/客户匹配。依赖 Phase 2 导入的知识库数据。

## Global Constraints

- 每个字段保存多来源结果（S13.6）
- 新客户/新物料不强行匹配旧数据（S13.7）
- 候选来源：OCR、MiMo、物料字典、历史配方、规则合法性
- 置信度分级：>=0.95 绿色，0.80-0.95 黄色，<0.80 红色

---

### Task 1: 物料/客户匹配器

**Covers:** [S8, S6]

**Files:**
- Create: `app/domain/matcher.py`
- Create: `app/tests/test_matcher.py`

- [ ] **Step 1: 创建匹配器**

```python
# app/domain/matcher.py
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import Material, Customer, Product, MaterialAlias


def match_material(name: str) -> list[dict]:
    """模糊匹配物料库，返回候选列表"""
    if not name:
        return []
    with get_session() as session:
        # 精确匹配
        exact = session.query(Material).filter(Material.standard_name == name).first()
        if exact:
            return [{"id": exact.id, "name": exact.standard_name, "confidence": 1.0, "source": "exact_match"}]

        # 别名匹配
        alias = session.query(MaterialAlias).filter(MaterialAlias.alias == name).first()
        if alias:
            mat = session.query(Material).get(alias.material_id)
            if mat:
                return [{"id": mat.id, "name": mat.standard_name, "confidence": 0.9, "source": "alias_match"}]

        # 模糊匹配
        materials = session.query(Material).filter(Material.standard_name.contains(name)).all()
        results = []
        for m in materials:
            results.append({"id": m.id, "name": m.standard_name, "confidence": 0.7, "source": "fuzzy_match"})
        return results[:5]


def match_customer(name: str) -> list[dict]:
    """模糊匹配客户库"""
    if not name:
        return []
    with get_session() as session:
        exact = session.query(Customer).filter(Customer.customer_name == name).first()
        if exact:
            return [{"id": exact.id, "name": exact.customer_name, "confidence": 1.0, "source": "exact_match"}]
        customers = session.query(Customer).filter(Customer.customer_name.contains(name)).all()
        return [{"id": c.id, "name": c.customer_name, "confidence": 0.7, "source": "fuzzy_match"} for c in customers[:5]]


def match_product(name: str, customer_id: int = None) -> list[dict]:
    """模糊匹配产品库"""
    if not name:
        return []
    with get_session() as session:
        q = session.query(Product)
        if customer_id:
            q = q.filter(Product.customer_id == customer_id)
        exact = q.filter(Product.product_name == name).first()
        if exact:
            return [{"id": exact.id, "name": exact.product_name, "confidence": 1.0, "source": "exact_match"}]
        products = q.filter(Product.product_name.contains(name)).all()
        return [{"id": p.id, "name": p.product_name, "confidence": 0.7, "source": "fuzzy_match"} for p in products[:5]]
```

- [ ] **Step 2: 编写测试**

```python
# app/tests/test_matcher.py
import pytest
from app.domain.matcher import match_material, match_customer, match_product
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import Material, Customer, Product, MaterialAlias


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def sample_data():
    with get_session() as session:
        mat = Material(standard_name="PP原料", category="树脂")
        session.add(mat)
        session.flush()
        session.add(MaterialAlias(material_id=mat.id, alias="PP", alias_type="MANUAL_ALIAS"))
        session.add(Customer(customer_name="客户A"))
        session.add(Product(product_name="产品X"))


def test_match_material_exact(sample_data):
    result = match_material("PP原料")
    assert len(result) == 1
    assert result[0]["confidence"] == 1.0


def test_match_material_alias(sample_data):
    result = match_material("PP")
    assert len(result) == 1
    assert result[0]["confidence"] == 0.9


def test_match_customer_exact(sample_data):
    result = match_customer("客户A")
    assert len(result) == 1
    assert result[0]["confidence"] == 1.0


def test_match_product_exact(sample_data):
    result = match_product("产品X")
    assert len(result) == 1
    assert result[0]["confidence"] == 1.0


def test_match_empty():
    assert match_material("") == []
    assert match_customer("") == []
```

- [ ] **Step 3: 运行测试并提交**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_matcher.py -v
git add app/domain/matcher.py app/tests/test_matcher.py
git commit -m "feat: material/customer/product matcher with exact, alias, and fuzzy matching"
```

---

### Task 2: 候选融合服务

**Covers:** [S8]

**Files:**
- Create: `app/application/fusion_service.py`
- Create: `app/tests/test_fusion_service.py`

- [ ] **Step 1: 创建融合服务**

```python
# app/application/fusion_service.py
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import FieldRecognitionResult, FieldCandidate
from app.domain.matcher import match_material
from app.configs import load_config


class FusionService:
    def __init__(self):
        self.rules = load_config("rules")

    def fuse_job(self, job_id: int) -> dict:
        """对一个 job 的所有字段执行候选融合"""
        with get_session() as session:
            fields = session.query(FieldRecognitionResult).filter_by(job_id=job_id).all()
            field_data = [(f.id, f.field_key, f.ocr_raw_text, f.ocr_confidence,
                          f.mimo_raw_text, f.mimo_confidence) for f in fields]

        fused_count = 0
        for field_id, field_key, ocr_text, ocr_conf, mimo_text, mimo_conf in field_data:
            candidates = []

            # OCR 候选
            if ocr_text:
                candidates.append({
                    "value": ocr_text, "confidence": ocr_conf or 0.5,
                    "source": "ocr", "rank": 0,
                })

            # MiMo 候选
            if mimo_text:
                candidates.append({
                    "value": mimo_text, "confidence": mimo_conf or 0.5,
                    "source": "mimo", "rank": 0,
                })

            # 物料字典匹配（仅对物料相关字段）
            if field_key in ("material_name",) and ocr_text:
                matches = match_material(ocr_text)
                for m in matches[:3]:
                    candidates.append({
                        "value": m["name"], "confidence": m["confidence"] * 0.8,
                        "source": f"dict_{m['source']}", "rank": 0,
                    })

            # 按置信度排序
            candidates.sort(key=lambda c: c["confidence"], reverse=True)
            for i, c in enumerate(candidates):
                c["rank"] = i + 1

            # 写入 field_candidates
            with get_session() as session:
                # 清除旧候选
                session.query(FieldCandidate).filter_by(field_result_id=field_id).delete()
                for c in candidates:
                    fc = FieldCandidate(
                        field_result_id=field_id,
                        candidate_value=c["value"],
                        source=c["source"],
                        confidence=c["confidence"],
                        rank=c["rank"],
                    )
                    session.add(fc)

                # 更新最终值为最高置信度候选
                if candidates:
                    best = candidates[0]
                    fr = session.query(FieldRecognitionResult).get(field_id)
                    fr.final_value = best["value"]
                    fr.final_confidence = best["confidence"]
                    fr.source = best["source"]

            fused_count += 1

        return {"job_id": job_id, "fused_fields": fused_count}
```

- [ ] **Step 2: 编写测试**

```python
# app/tests/test_fusion_service.py
import pytest
from app.application.fusion_service import FusionService
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine, get_session
from app.infrastructure.database.models import (
    RecognitionJob, ProductionRecord, FieldRecognitionResult, FieldCandidate
)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def job_with_fields():
    with get_session() as session:
        job = RecognitionJob(job_no="TEST-FUSION-001", status="NEED_REVIEW")
        session.add(job)
        session.flush()
        rec = ProductionRecord(job_id=job.id, record_index=0)
        session.add(rec)
        session.flush()
        fr = FieldRecognitionResult(
            job_id=job.id, record_id=rec.id, field_key="time",
            ocr_raw_text="08:30", ocr_confidence=0.9,
            mimo_raw_text="08:30", mimo_confidence=0.95,
        )
        session.add(fr)
        return job.id


def test_fuse_creates_candidates(job_with_fields):
    service = FusionService()
    result = service.fuse_job(job_with_fields)
    assert result["fused_fields"] == 1
    with get_session() as session:
        cands = session.query(FieldCandidate).all()
        assert len(cands) >= 2  # OCR + MiMo


def test_fuse_updates_final_value(job_with_fields):
    service = FusionService()
    service.fuse_job(job_with_fields)
    with get_session() as session:
        fr = session.query(FieldRecognitionResult).filter_by(job_id=job_with_fields).first()
        assert fr.final_value == "08:30"
        assert fr.final_confidence >= 0.9
```

- [ ] **Step 3: 运行测试并提交**

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_fusion_service.py -v
git add app/application/fusion_service.py app/tests/test_fusion_service.py
git commit -m "feat: candidate fusion service with multi-source ranking"
```

---

### Task 3: 融合 API 端点

**Covers:** [S8, S12]

**Files:**
- Modify: `app/interfaces/api_routes.py`
- Create: `app/tests/test_fusion_api.py`

- [ ] **Step 1: 添加融合 API**

```python
from app.application.fusion_service import FusionService
fusion_service = FusionService()

@router.post("/jobs/{job_id}/fuse")
async def fuse_job(job_id: int):
    try:
        result = fusion_service.fuse_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: 编写测试并提交**

```python
# app/tests/test_fusion_api.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@patch("app.interfaces.api_routes.fusion_service")
def test_fuse_job(mock_service):
    mock_service.fuse_job.return_value = {"job_id": 1, "fused_fields": 10}
    resp = client.post("/api/jobs/1/fuse")
    assert resp.status_code == 200
```

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_fusion_api.py -v
git add app/interfaces/api_routes.py app/tests/test_fusion_api.py
git commit -m "feat: fusion API endpoint"
```
