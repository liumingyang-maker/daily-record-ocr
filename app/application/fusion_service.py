"""Fusion service — merges OCR + MiMo candidates and picks final value."""

from app.configs import load_config
from app.domain.matcher import match_material
from app.infrastructure.database.models import (
    FieldCandidate,
    FieldRecognitionResult,
    RecognitionJob,
)
from app.infrastructure.database.session import get_session


MATERIAL_FIELD_KEYS = {"material_name", "material_name_raw"}


class FusionService:
    def __init__(self):
        self.rules = load_config("rules")

    def fuse_job(self, job_id: int) -> dict:
        with get_session() as session:
            job = session.get(RecognitionJob, job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")

            field_results = (
                session.query(FieldRecognitionResult)
                .filter_by(job_id=job_id)
                .all()
            )

            fused_count = 0
            for fr in field_results:
                self._fuse_field(session, fr)
                fused_count += 1

            session.flush()

        return {"job_id": job_id, "fused_fields": fused_count}

    def _fuse_field(self, session, fr: FieldRecognitionResult) -> None:
        # Clear old candidates
        session.query(FieldCandidate).filter_by(field_result_id=fr.id).delete()

        candidates: list[dict] = []

        # OCR candidate
        if fr.ocr_raw_text and fr.ocr_raw_text.strip():
            candidates.append(
                {
                    "candidate_value": fr.ocr_raw_text.strip(),
                    "source": "ocr",
                    "confidence": fr.ocr_confidence or 0.0,
                }
            )

        # MiMo candidate
        if fr.mimo_raw_text and fr.mimo_raw_text.strip():
            candidates.append(
                {
                    "candidate_value": fr.mimo_raw_text.strip(),
                    "source": "mimo",
                    "confidence": fr.mimo_confidence or 0.0,
                }
            )

        # Material dict candidates
        if fr.field_key in MATERIAL_FIELD_KEYS:
            raw = fr.ocr_raw_text or fr.mimo_raw_text or ""
            if raw.strip():
                dict_matches = match_material(raw.strip(), session)
                for m in dict_matches:
                    candidates.append(
                        {
                            "candidate_value": m["name"],
                            "source": f"dict_{m['source']}",
                            "confidence": m["confidence"],
                        }
                    )

        # Deduplicate by (candidate_value, source), keep highest confidence
        seen: dict[tuple, dict] = {}
        for c in candidates:
            key = (c["candidate_value"], c["source"])
            if key not in seen or c["confidence"] > seen[key]["confidence"]:
                seen[key] = c
        candidates = list(seen.values())

        # Sort by confidence descending
        candidates.sort(key=lambda c: c["confidence"], reverse=True)

        # Write candidates to DB
        for rank, c in enumerate(candidates, start=1):
            session.add(
                FieldCandidate(
                    field_result_id=fr.id,
                    candidate_value=c["candidate_value"],
                    source=c["source"],
                    confidence=c["confidence"],
                    rank=rank,
                )
            )

        # Update final value on the field result
        if candidates:
            best = candidates[0]
            fr.final_value = best["candidate_value"]
            fr.final_confidence = best["confidence"]
            fr.source = best["source"]
