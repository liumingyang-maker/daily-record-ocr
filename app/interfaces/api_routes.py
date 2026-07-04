"""API routes."""

from fastapi import APIRouter, HTTPException, UploadFile

from app.application.mimo_service import MimoService
from app.application.ocr_service import OcrService
from app.application.preprocess_service import process
from app.application.upload_service import create_job, get_job, list_jobs

api_router = APIRouter()


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@api_router.post("/jobs/upload")
async def upload_job(file: UploadFile):
    try:
        job = await create_job(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job.id, "job_no": job.job_no, "status": job.status}


@api_router.get("/jobs")
async def api_list_jobs(limit: int = 50):
    jobs = list_jobs(limit=limit)
    return [
        {
            "id": j.id,
            "job_no": j.job_no,
            "status": j.status,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


@api_router.get("/jobs/{job_id}")
async def api_get_job(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "job_no": job.job_no,
        "status": job.status,
        "source_image_path": job.source_image_path,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "error_message": job.error_message,
    }


@api_router.post("/jobs/{job_id}/preprocess")
async def preprocess_job(job_id: int):
    try:
        result = process(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


ocr_service = OcrService()


@api_router.post("/jobs/{job_id}/recognize")
async def recognize_job(job_id: int):
    try:
        result = ocr_service.recognize_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


mimo_service = MimoService()


@api_router.post("/jobs/{job_id}/mimo")
async def mimo_recognize_job(job_id: int):
    try:
        result = mimo_service.recognize_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
