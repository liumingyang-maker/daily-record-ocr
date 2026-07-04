"""MiMo recognition service — runs MiMo vision API on preprocessed records."""

import hashlib
import json
import time

import cv2

from app.configs import load_config
from app.infrastructure.database.models import (
    FieldRecognitionResult,
    MimoCache,
    MimoRequestLog,
    ProductionRecord,
    RecognitionJob,
)
from app.infrastructure.database.session import get_session
from app.infrastructure.image.cropper import crop_field_cells
from app.infrastructure.vision import get_mimo_client


class MimoService:
    def __init__(self):
        self.template = load_config("template_daily_record_v1")["template"]
        self.mimo_config = load_config("mimo")["mimo"]

    def recognize_job(self, job_id: int) -> dict:
        client = get_mimo_client()
        if client is None:
            raise ValueError("MiMo client not configured")

        with get_session() as session:
            job = session.get(RecognitionJob, job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")

            records = (
                session.query(ProductionRecord)
                .filter_by(job_id=job_id)
                .order_by(ProductionRecord.record_index)
                .all()
            )

            prompt_version = self.mimo_config.get("prompt_version", "")
            model = self.mimo_config.get("model", "")
            cache_enabled = self.mimo_config.get("cache_enabled", True)

            all_results: list[dict] = []
            for rec in records:
                img = cv2.imread(rec.record_crop_path)
                if img is None:
                    continue

                field_cells = crop_field_cells(
                    img, self.template, str(job_id), rec.record_index
                )

                for field_name, cell_path in field_cells.items():
                    result = self._process_field(
                        session,
                        client,
                        job_id,
                        rec.id,
                        field_name,
                        cell_path,
                        prompt_version,
                        model,
                        cache_enabled,
                    )
                    all_results.append(result)

            job.mimo_used = True
            session.flush()

        return {
            "job_id": job_id,
            "processed_fields": len(all_results),
            "results": all_results,
        }

    def _process_field(
        self,
        session,
        client,
        job_id: int,
        record_id: int,
        field_name: str,
        cell_path: str,
        prompt_version: str,
        model: str,
        cache_enabled: bool,
    ) -> dict:
        image_hash = _file_hash(cell_path)

        if cache_enabled:
            cached = self._check_cache(session, image_hash, prompt_version, model)
            if cached is not None:
                self._update_field_result(
                    session, job_id, record_id, field_name, cached
                )
                return {
                    "field_key": field_name,
                    "source": "cache",
                    "mimo_raw_text": cached.get("raw_text", ""),
                    "mimo_confidence": cached.get("confidence", 0.0),
                }

        start = time.time()
        mimo_result = client.recognize_record(cell_path)
        latency_ms = int((time.time() - start) * 1000)

        session.add(
            MimoRequestLog(
                job_id=job_id,
                record_id=record_id,
                request_type="record_level",
                model=model,
                prompt_version=prompt_version,
                image_hash=image_hash,
                response_json={"fields": mimo_result.fields} if mimo_result.success else None,
                success=mimo_result.success,
                error_message=mimo_result.error or None,
                latency_ms=latency_ms,
            )
        )

        if mimo_result.success and cache_enabled:
            session.add(
                MimoCache(
                    image_hash=image_hash,
                    prompt_version=prompt_version,
                    model=model,
                    response_json={"fields": mimo_result.fields},
                )
            )

        field_data = mimo_result.fields.get(field_name, {})
        raw_text = field_data.get("raw_text", "")
        confidence = field_data.get("confidence", 0.0)

        self._update_field_result(
            session,
            job_id,
            record_id,
            field_name,
            {"raw_text": raw_text, "confidence": confidence},
        )

        return {
            "field_key": field_name,
            "source": "mimo",
            "mimo_raw_text": raw_text,
            "mimo_confidence": confidence,
        }

    def _check_cache(
        self, session, image_hash: str, prompt_version: str, model: str
    ) -> dict | None:
        cached = (
            session.query(MimoCache)
            .filter_by(
                image_hash=image_hash,
                prompt_version=prompt_version,
                model=model,
            )
            .first()
        )
        if cached and cached.response_json:
            fields = cached.response_json.get("fields", {})
            # Return the first field's data as a generic cached result
            for field_data in fields.values():
                return field_data
        return None

    def _update_field_result(
        self, session, job_id: int, record_id: int, field_name: str, data: dict
    ) -> None:
        field_result = (
            session.query(FieldRecognitionResult)
            .filter_by(job_id=job_id, record_id=record_id, field_key=field_name)
            .first()
        )
        if field_result:
            field_result.mimo_raw_text = data.get("raw_text", "")
            field_result.mimo_confidence = data.get("confidence", 0.0)


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
