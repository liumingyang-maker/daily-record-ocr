"""Preprocessing service — end-to-end image correction, cropping, and DB persistence."""

import cv2

from app.configs import load_config
from app.infrastructure.database.models import ProductionRecord, RecognitionJob
from app.infrastructure.database.session import get_session
from app.infrastructure.image.cropper import (
    crop_field_cells,
    crop_record_blocks,
    save_record_crops,
)
from app.infrastructure.image.preprocessor import preprocess_image


def process(job_id: int) -> dict:
    """Run full preprocessing pipeline for a recognition job.

    Returns dict with job_id, corrected_path, records_count, field_crops.
    """
    with get_session() as session:
        job = session.get(RecognitionJob, job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")
        source_path = job.source_image_path
        job.status = "PREPROCESSING"
        session.flush()

    # Preprocess image (outside DB session — heavy I/O)
    corrected_path = preprocess_image(source_path, str(job_id))

    # Read corrected image
    img = cv2.imread(str(corrected_path))
    if img is None:
        raise RuntimeError(f"Failed to read corrected image: {corrected_path}")

    # Load template and crop
    template = load_config("template_daily_record_v1")["template"]
    records = crop_record_blocks(img, template, str(job_id))
    records = save_record_crops(records, str(job_id))

    field_crops: list[dict[str, str]] = []
    for rec in records:
        cells = crop_field_cells(rec["image"], template, str(job_id), rec["index"])
        field_crops.append(cells)

    # Persist to DB
    with get_session() as session:
        job = session.get(RecognitionJob, job_id)
        job.status = "PREPROCESSED"
        job.corrected_image_path = str(corrected_path)

        for rec in records:
            pr = ProductionRecord(
                job_id=job_id,
                record_index=rec["index"],
                record_crop_path=rec["path"],
            )
            session.add(pr)

        session.flush()

    return {
        "job_id": job_id,
        "corrected_path": str(corrected_path),
        "records_count": len(records),
        "field_crops": field_crops,
    }
