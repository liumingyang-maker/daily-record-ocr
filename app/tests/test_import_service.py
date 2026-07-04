"""Tests for ImportService — staging暂存."""

import hashlib
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import *  # noqa: F401,F403
from app.infrastructure.database.models import (
    ImportBatch,
    ImportStagingRecord,
)
from app.infrastructure.history_import import load_import_profiles


@pytest.fixture()
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture()
def xlsx_file(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "批号", "物料", "用量"])
    ws.append(["2025-01-01", "客户A", "产品X", "B001", "物料1", 10.5])
    ws.append(["2025-01-02", "客户B", "产品Y", "B002", "物料2", 20.0])
    path = tmp_path / "import_test.xlsx"
    wb.save(path)
    return str(path)


@pytest.fixture()
def patch_session(monkeypatch, db_session):
    """Patch get_session to use the test in-memory database."""
    from contextlib import contextmanager

    @contextmanager
    def _mock_session():
        yield db_session
        db_session.commit()

    monkeypatch.setattr(
        "app.application.import_service.get_session", _mock_session
    )


@pytest.fixture()
def patch_imports_dir(monkeypatch, tmp_path):
    """Patch HISTORY_IMPORTS_DIR to a temp directory."""
    imports_dir = tmp_path / "history_imports"
    imports_dir.mkdir()
    monkeypatch.setattr(
        "app.application.import_service.HISTORY_IMPORTS_DIR", imports_dir
    )
    return imports_dir


def test_upload_and_parse_creates_batch(
    xlsx_file, patch_session, patch_imports_dir
):
    from app.application.import_service import ImportService

    svc = ImportService()
    batch = svc.upload_and_parse(xlsx_file, "type_a_flat")

    assert batch.id is not None
    assert batch.batch_no.startswith("IMP")
    assert batch.status == "PARSED"
    assert batch.import_profile == "type_a_flat"
    assert batch.total_rows == 2
    assert batch.source_file_name == "import_test.xlsx"


def test_upload_and_parse_creates_staging_records(
    xlsx_file, patch_session, patch_imports_dir
):
    from app.application.import_service import ImportService

    svc = ImportService()
    batch = svc.upload_and_parse(xlsx_file, "type_a_flat")

    assert len(batch.staging_records) == 2
    rec0 = batch.staging_records[0]
    assert rec0.record_index == 0
    assert rec0.normalized_payload_json["date"] == "2025-01-01"
    assert rec0.normalized_payload_json["customer"] == "客户A"
    assert rec0.normalized_payload_json["usage"] == 10.5
    assert rec0.normalized_payload_json["unit"] == "kg"
    assert rec0.is_valid is True
    assert rec0.is_selected is True

    rec1 = batch.staging_records[1]
    assert rec1.record_index == 1
    assert rec1.normalized_payload_json["customer"] == "客户B"


def test_upload_and_parse_copies_file(
    xlsx_file, patch_session, patch_imports_dir
):
    from app.application.import_service import ImportService

    svc = ImportService()
    batch = svc.upload_and_parse(xlsx_file, "type_a_flat")

    copied = Path(batch.source_file_path)
    assert copied.exists()
    assert copied.parent == patch_imports_dir


def test_get_batch(xlsx_file, patch_session, patch_imports_dir):
    from app.application.import_service import ImportService

    svc = ImportService()
    batch = svc.upload_and_parse(xlsx_file, "type_a_flat")

    fetched = svc.get_batch(batch.id)
    assert fetched is not None
    assert fetched.id == batch.id
    assert fetched.batch_no == batch.batch_no


def test_get_batch_not_found(patch_session):
    from app.application.import_service import ImportService

    svc = ImportService()
    assert svc.get_batch(99999) is None


def test_list_batches(xlsx_file, patch_session, patch_imports_dir):
    from app.application.import_service import ImportService

    svc = ImportService()
    batch1 = svc.upload_and_parse(xlsx_file, "type_a_flat")

    # Create another file for a second batch
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "客户", "产品", "批号", "物料", "用量"])
    ws.append(["2025-03-01", "客户C", "产品Z", "B003", "物料3", 5.0])
    path2 = Path(xlsx_file).parent / "import_test2.xlsx"
    wb.save(path2)

    batch2 = svc.upload_and_parse(str(path2), "type_a_flat")

    batches = svc.list_batches()
    assert len(batches) == 2
    batch_ids = {b.id for b in batches}
    assert batch1.id in batch_ids
    assert batch2.id in batch_ids


def test_list_batches_empty(patch_session):
    from app.application.import_service import ImportService

    svc = ImportService()
    assert svc.list_batches() == []
