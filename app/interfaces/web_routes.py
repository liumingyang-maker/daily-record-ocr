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
