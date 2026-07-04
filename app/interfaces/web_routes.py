"""Web page routes."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.application.import_service import ImportService
from app.application.upload_service import get_job, list_jobs
from app.infrastructure.history_import import load_import_profiles

templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

web_router = APIRouter()
import_service = ImportService()


@web_router.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"title": "首页"})


@web_router.get("/jobs")
async def jobs_page(request: Request):
    jobs = list_jobs(limit=50)
    return templates.TemplateResponse(request=request, name="jobs.html", context={"title": "识别任务", "jobs": jobs})


@web_router.get("/jobs/{job_id}")
async def job_detail_page(request: Request, job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse(request=request, name="job_detail.html", context={"request": request, "title": f"任务详情 - {job.job_no}", "job": job})


@web_router.get("/history-import")
async def history_import_page(request: Request):
    batches = import_service.list_batches()
    profiles = load_import_profiles()
    return templates.TemplateResponse(request=request, name="history_import.html", context={
        "title": "历史记录导入",
        "batches": batches,
        "profiles": profiles,
    })


@web_router.get("/history-import/{batch_id}")
async def import_detail_page(request: Request, batch_id: int):
    batch = import_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return templates.TemplateResponse(request=request, name="import_detail.html", context={
        "request": request, "title": f"导入详情 - {batch.batch_no}", "batch": batch,
    })


@web_router.get("/jobs/{job_id}/review")
async def job_review_page(request: Request, job_id: int):
    from app.infrastructure.database.session import get_session
    from app.infrastructure.database.models import RecognitionJob, ProductionRecord, FieldRecognitionResult, FieldCandidate

    with get_session() as session:
        job = session.get(RecognitionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        records = session.query(ProductionRecord).filter(ProductionRecord.job_id == job_id).order_by(ProductionRecord.record_index).all()
        field_results = session.query(FieldRecognitionResult).filter(FieldRecognitionResult.job_id == job_id).all()
        candidates = session.query(FieldCandidate).filter(FieldCandidate.field_result_id.in_([f.id for f in field_results])).all()

        # Build candidate map: field_result_id -> list of candidates
        candidate_map = {}
        for c in candidates:
            candidate_map.setdefault(c.field_result_id, []).append(c)

        # Build field map: record_id -> list of field results
        field_map = {}
        for f in field_results:
            field_map.setdefault(f.record_id, []).append(f)

    return templates.TemplateResponse(request=request, name="job_review.html", context={
        "request": request,
        "title": f"人工确认 - {job.job_no}",
        "job": job,
        "records": records,
        "field_map": field_map,
        "candidate_map": candidate_map,
    })
