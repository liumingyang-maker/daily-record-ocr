"""OCR recognition service — runs field-level OCR on preprocessed records."""

import cv2

from app.configs import load_config
from app.infrastructure.database.models import (
    FieldRecognitionResult,
    ProductionRecord,
    RecognitionJob,
)
from app.infrastructure.database.session import get_session
from app.infrastructure.image.cropper import crop_field_cells
from app.infrastructure.ocr import get_ocr_engine

CONFIDENCE_THRESHOLD = 0.95


class OcrService:
    def __init__(self):
        self.template = load_config("template_daily_record_v1")["template"]
        self.ocr_engine = get_ocr_engine()

    def recognize_job(self, job_id: int) -> dict:
        with get_session() as session:
            job = session.get(RecognitionJob, job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")
            if job.status != "PREPROCESSED":
                raise ValueError(
                    f"Job {job_id} status is '{job.status}', expected 'PREPROCESSED'"
                )
            job.status = "RECOGNIZING"
            session.flush()

            records = (
                session.query(ProductionRecord)
                .filter_by(job_id=job_id)
                .order_by(ProductionRecord.record_index)
                .all()
            )

            all_results: list[dict] = []
            for rec in records:
                img = cv2.imread(rec.record_crop_path)
                if img is None:
                    continue

                field_cells = crop_field_cells(
                    img, self.template, str(job_id), rec.record_index
                )

                for field_name, cell_path in field_cells.items():
                    ocr_result = self.ocr_engine.recognize(cell_path)
                    need_review = ocr_result.confidence < CONFIDENCE_THRESHOLD

                    field_result = FieldRecognitionResult(
                        job_id=job_id,
                        record_id=rec.id,
                        field_key=field_name,
                        cell_crop_path=cell_path,
                        ocr_raw_text=ocr_result.text,
                        ocr_confidence=ocr_result.confidence,
                        final_value=ocr_result.text,
                        final_confidence=ocr_result.confidence,
                        source="ocr",
                        need_review=need_review,
                    )
                    session.add(field_result)
                    all_results.append(
                        {
                            "field_key": field_name,
                            "ocr_raw_text": ocr_result.text,
                            "ocr_confidence": ocr_result.confidence,
                            "need_review": need_review,
                        }
                    )

            job.status = "NEED_REVIEW"
            session.flush()

        return {
            "job_id": job_id,
            "recognized_fields": len(all_results),
            "results": all_results,
        }
