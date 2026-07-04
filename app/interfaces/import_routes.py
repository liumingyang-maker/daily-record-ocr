"""Import API routes."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.application.import_service import ImportService

import_router = APIRouter()

SUPPORTED_EXTENSIONS = {".xlsx", ".csv"}

import_service = ImportService()


@import_router.post("/upload")
async def upload_import_file(
    file: UploadFile = File(...),
    profile: str = Form(...),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    suffix = ext
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        batch = import_service.upload_and_parse(tmp_path, profile)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown import profile: {profile}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "batch_id": batch.id,
        "batch_no": batch.batch_no,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "import_profile": batch.import_profile,
    }


@import_router.get("/batches")
async def list_import_batches():
    batches = import_service.list_batches()
    return [
        {
            "id": b.id,
            "batch_no": b.batch_no,
            "status": b.status,
            "source_file_name": b.source_file_name,
            "import_profile": b.import_profile,
            "total_rows": b.total_rows,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in batches
    ]


@import_router.get("/batches/{batch_id}")
async def get_import_batch(batch_id: int):
    batch = import_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {
        "id": batch.id,
        "batch_no": batch.batch_no,
        "status": batch.status,
        "source_file_name": batch.source_file_name,
        "import_profile": batch.import_profile,
        "total_rows": batch.total_rows,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "staging_records": [
            {
                "id": r.id,
                "record_index": r.record_index,
                "is_valid": r.is_valid,
                "is_selected": r.is_selected,
                "raw_payload_json": r.raw_payload_json,
                "normalized_payload_json": r.normalized_payload_json,
            }
            for r in batch.staging_records
        ],
    }


@import_router.post("/batches/{batch_id}/confirm")
async def confirm_import(batch_id: int):
    try:
        batch = import_service.confirm_and_import(batch_id)
        return {"batch_id": batch.id, "batch_no": batch.batch_no, "status": batch.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
