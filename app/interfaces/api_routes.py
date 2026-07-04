"""API routes."""

from fastapi import APIRouter, HTTPException, UploadFile

from app.application.export_service import ExportService
from app.application.fusion_service import FusionService
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


fusion_service = FusionService()


@api_router.post("/jobs/{job_id}/fuse")
async def fuse_job(job_id: int):
    try:
        result = fusion_service.fuse_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@api_router.patch("/fields/{field_id}")
async def update_field(field_id: int, body: dict):
    from app.infrastructure.database.session import get_session
    from app.infrastructure.database.models import FieldRecognitionResult, ManualCorrectionLog

    final_value = body.get("final_value")
    if final_value is None:
        raise HTTPException(status_code=400, detail="final_value is required")

    with get_session() as session:
        field = session.get(FieldRecognitionResult, field_id)
        if not field:
            raise HTTPException(status_code=404, detail="Field not found")

        old_value = field.final_value
        field.final_value = final_value
        field.manual_corrected = True

        log = ManualCorrectionLog(
            record_id=field.record_id,
            field_key=field.field_key,
            old_value=old_value,
            new_value=final_value,
            correction_type="OTHER",
        )
        session.add(log)
        session.flush()

        return {
            "field_id": field.id,
            "final_value": field.final_value,
            "manual_corrected": field.manual_corrected,
            "log_id": log.id,
        }


@api_router.post("/jobs/{job_id}/confirm")
async def confirm_job(job_id: int):
    from app.infrastructure.database.session import get_session
    from app.infrastructure.database.models import RecognitionJob

    with get_session() as session:
        job = session.get(RecognitionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status not in ("NEED_REVIEW", "RECOGNIZED"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm job with status {job.status}",
            )

        job.status = "CONFIRMED"
        session.flush()

        return {
            "job_id": job.id,
            "job_no": job.job_no,
            "status": job.status,
        }


export_service = ExportService()


@api_router.post("/jobs/{job_id}/export")
async def export_job(job_id: int):
    try:
        result = export_service.export_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@api_router.get("/settings")
async def api_get_settings():
    from app.application.settings_service import get_settings
    return get_settings()


@api_router.post("/settings")
async def api_save_settings(body: dict):
    from app.application.settings_service import save_settings
    save_settings(body)
    return {"status": "ok", "message": "设置已保存"}


@api_router.post("/settings/test-mimo")
async def test_mimo_connection():
    """Test MiMo API connection with current settings."""
    from app.application.settings_service import read_env
    env = read_env()
    api_key = env.get("MIMO_API_KEY", "")
    if not api_key:
        return {"success": False, "message": "未配置 API Key"}

    # If using mock client, report mock status
    from app.infrastructure.vision import get_mimo_client
    from app.infrastructure.vision.mock_mimo_client import MockMimoClient
    client = get_mimo_client()
    if isinstance(client, MockMimoClient):
        return {"success": True, "message": "当前使用 Mock 模式（无需真实 API）"}

    # Try a real connection test
    try:
        result = client.recognize_record("test")
        return {"success": True, "message": f"连接成功，模型响应正常"}
    except Exception as e:
        return {"success": False, "message": str(e)}
