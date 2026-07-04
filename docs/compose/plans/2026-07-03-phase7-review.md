# Phase 7: 人工确认页面 Implementation Plan

**Goal:** 实现人工确认 Web 页面，用户可以查看识别结果、修正字段值、确认记录。

## Global Constraints

- 所有不确定字段进入人工确认（S8）
- 保留人工修正日志（S13.8）
- 第一版：所有记录进入人工确认页面，由用户一键确认

---

### Task 1: 确认页面 Web 路由和模板

**Covers:** [S8, S12]

**Files:**
- Create: `app/interfaces/templates/job_review.html`
- Modify: `app/interfaces/web_routes.py`

- [ ] **Step 1: 添加确认页面路由**

在 `app/interfaces/web_routes.py` 中添加：

```python
@router.get("/jobs/{job_id}/review")
async def job_review_page(request: Request, job_id: int):
    from app.infrastructure.database.session import get_session
    from app.infrastructure.database.models import RecognitionJob, ProductionRecord, FieldRecognitionResult, FieldCandidate
    with get_session() as session:
        job = session.query(RecognitionJob).get(job_id)
        if not job:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Job not found")
        records = session.query(ProductionRecord).filter_by(job_id=job_id).all()
        fields = session.query(FieldRecognitionResult).filter_by(job_id=job_id).all()
        candidates = {}
        for f in fields:
            cands = session.query(FieldCandidate).filter_by(field_result_id=f.id).order_by(FieldCandidate.rank).all()
            candidates[f.id] = cands
    return templates.TemplateResponse("job_review.html", {
        "request": request, "title": f"确认 - {job.job_no}",
        "job": job, "records": records, "fields": fields, "candidates": candidates,
    })
```

- [ ] **Step 2: 创建确认页面模板**

```html
<!-- app/interfaces/templates/job_review.html -->
{% extends "base.html" %}
{% block content %}
<div class="page-header">
    <h1>识别确认: {{ job.job_no }}</h1>
    <div>
        <a href="/jobs/{{ job.id }}" class="btn">返回详情</a>
        <button id="confirm-btn" class="btn btn-success" onclick="confirmAll()">全部确认</button>
    </div>
</div>

{% for record in records %}
<div class="card" style="margin-bottom:20px">
    <h3>记录 #{{ record.record_index + 1 }}</h3>
    <table>
        <thead><tr><th>字段</th><th>识别值</th><th>置信度</th><th>来源</th><th>候选值</th><th>操作</th></tr></thead>
        <tbody>
        {% for field in fields if field.record_id == record.id %}
        <tr>
            <td><strong>{{ field.field_key }}</strong></td>
            <td>
                <input type="text" class="field-value" data-field-id="{{ field.id }}"
                       value="{{ field.final_value or '' }}" style="width:200px">
            </td>
            <td>
                <span class="confidence {% if field.final_confidence and field.final_confidence >= 0.95 %}conf-green{% elif field.final_confidence and field.final_confidence >= 0.80 %}conf-yellow{% else %}conf-red{% endif %}">
                    {{ "%.1f"|format((field.final_confidence or 0) * 100) }}%
                </span>
            </td>
            <td>{{ field.source or '-' }}</td>
            <td>
                {% for cand in candidates.get(field.id, []) %}
                <span class="candidate" onclick="applyCandidate({{ field.id }}, '{{ cand.candidate_value }}')"
                      title="{{ cand.source }}: {{ "%.0f"|format((cand.confidence or 0) * 100) }}%">
                    {{ cand.candidate_value }}
                </span>
                {% endfor %}
            </td>
            <td><button class="btn btn-sm" onclick="saveField({{ field.id }})">保存</button></td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
</div>
{% endfor %}

<script>
function applyCandidate(fieldId, value) {
    document.querySelector(`.field-value[data-field-id="${fieldId}"]`).value = value;
}

async function saveField(fieldId) {
    const input = document.querySelector(`.field-value[data-field-id="${fieldId}"]`);
    const resp = await fetch(`/api/fields/${fieldId}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({value: input.value}),
    });
    if (resp.ok) {
        input.style.borderColor = 'green';
        setTimeout(() => input.style.borderColor = '', 1000);
    }
}

async function confirmAll() {
    if (!confirm('确认所有记录？')) return;
    const resp = await fetch('/api/jobs/{{ job.id }}/confirm', {method: 'POST'});
    if (resp.ok) {
        alert('确认成功');
        window.location.href = '/jobs/{{ job.id }}';
    }
}
</script>

<style>
.confidence { padding: 2px 8px; border-radius: 4px; font-weight: bold; }
.conf-green { background: #dcfce7; color: #16a34a; }
.conf-yellow { background: #fef3c7; color: #d97706; }
.conf-red { background: #fee2e2; color: #dc2626; }
.candidate { display: inline-block; padding: 2px 6px; margin: 2px; background: #f0f0f0;
             border-radius: 3px; cursor: pointer; font-size: 12px; }
.candidate:hover { background: #e0e0e0; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
</style>
{% endblock %}
```

- [ ] **Step 3: 提交**

```bash
git add app/interfaces/templates/job_review.html app/interfaces/web_routes.py
git commit -m "feat: human review page with field editing and candidate selection"
```

---

### Task 2: 字段更新和确认 API

**Covers:** [S8, S13]

**Files:**
- Modify: `app/interfaces/api_routes.py`
- Create: `app/tests/test_review_api.py`

- [ ] **Step 1: 添加字段更新和确认 API**

```python
@router.patch("/fields/{field_id}")
async def update_field(field_id: int, body: dict):
    from app.infrastructure.database.session import get_session
    from app.infrastructure.database.models import FieldRecognitionResult, ManualCorrectionLog
    value = body.get("value")
    with get_session() as session:
        fr = session.query(FieldRecognitionResult).get(field_id)
        if not fr:
            raise HTTPException(status_code=404, detail="Field not found")
        old_value = fr.final_value
        fr.final_value = value
        fr.manual_corrected = True
        fr.manual_value = value
        # 记录修正日志
        log = ManualCorrectionLog(
            record_id=fr.record_id, field_key=fr.field_key,
            old_value=old_value, new_value=value,
            correction_type="OTHER",
        )
        session.add(log)
    return {"field_id": field_id, "value": value}


@router.post("/jobs/{job_id}/confirm")
async def confirm_job(job_id: int):
    from app.infrastructure.database.session import get_session
    from app.infrastructure.database.models import RecognitionJob
    import datetime
    with get_session() as session:
        job = session.query(RecognitionJob).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job.status = "CONFIRMED"
        job.updated_at = datetime.datetime.utcnow()
    return {"job_id": job_id, "status": "CONFIRMED"}
```

- [ ] **Step 2: 编写测试并提交**

```python
# app/tests/test_review_api.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@patch("app.interfaces.api_routes.get_session")
def test_update_field(mock_session_ctx):
    mock_session = MagicMock()
    mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
    mock_fr = MagicMock()
    mock_fr.final_value = "old"
    mock_fr.record_id = 1
    mock_fr.field_key = "time"
    mock_session.query.return_value.get.return_value = mock_fr
    resp = client.patch("/api/fields/1", json={"value": "09:00"})
    assert resp.status_code == 200


@patch("app.interfaces.api_routes.get_session")
def test_confirm_job(mock_session_ctx):
    mock_session = MagicMock()
    mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
    mock_job = MagicMock()
    mock_session.query.return_value.get.return_value = mock_job
    resp = client.post("/api/jobs/1/confirm")
    assert resp.status_code == 200
```

```bash
cd /home/brian/Desktop/daily_record_ocr
.venv/bin/python -m pytest app/tests/test_review_api.py -v
git add app/interfaces/api_routes.py app/tests/test_review_api.py
git commit -m "feat: field update and job confirm API with correction logging"
```
