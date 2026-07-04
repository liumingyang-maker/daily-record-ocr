"""Import service — staging暂存 for history record imports."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path

from app.infrastructure.database.models import ImportBatch, ImportStagingRecord
from app.infrastructure.database.session import get_session
from app.infrastructure.history_import import load_import_profiles
from app.infrastructure.history_import.file_parser import parse_file
from app.settings import HISTORY_IMPORTS_DIR


class ImportService:
    def upload_and_parse(
        self, file_path: str, profile_name: str
    ) -> ImportBatch:
        profiles = load_import_profiles()
        profile = profiles[profile_name]

        # Copy file to HISTORY_IMPORTS_DIR
        HISTORY_IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
        src = Path(file_path)
        dest = HISTORY_IMPORTS_DIR / src.name
        shutil.copy2(src, dest)

        # Compute file hash
        file_hash = hashlib.sha256(src.read_bytes()).hexdigest()

        # Parse file
        rows = parse_file(file_path, profile)

        # Create batch + staging records
        batch_no = f"IMP{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        with get_session() as session:
            batch = ImportBatch(
                batch_no=batch_no,
                source_file_path=str(dest),
                source_file_name=src.name,
                file_hash=file_hash,
                import_profile=profile_name,
                status="PARSED",
                total_rows=len(rows),
            )
            session.add(batch)
            session.flush()

            for i, raw_row in enumerate(rows):
                normalized = self._normalize_row(raw_row, profile)
                rec = ImportStagingRecord(
                    batch_id=batch.id,
                    source_row_start=raw_row.get("_source_row"),
                    record_index=i,
                    raw_payload_json=raw_row,
                    normalized_payload_json=normalized,
                    is_valid=True,
                    is_selected=True,
                )
                session.add(rec)

            session.flush()
            session.refresh(batch)
            session.expunge(batch)
            return batch

    def _normalize_row(self, raw_row: dict, profile: dict) -> dict:
        """Extract field values from raw_row, applying defaults from profile."""
        result = {}
        for col_key, col_def in profile["columns"].items():
            value = raw_row.get(col_key)
            if value is None and "default" in col_def:
                value = col_def["default"]
            result[col_key] = value
        return result

    def get_batch(self, batch_id: int) -> ImportBatch | None:
        with get_session() as session:
            batch = session.get(ImportBatch, batch_id)
            if batch:
                session.refresh(batch)
                session.expunge(batch)
            return batch

    def list_batches(self) -> list[ImportBatch]:
        with get_session() as session:
            batches = (
                session.query(ImportBatch)
                .order_by(ImportBatch.created_at.desc())
                .all()
            )
            for b in batches:
                session.refresh(b)
                session.expunge(b)
            return batches
