"""Tests for ImportService.confirm_and_import — staging → production tables."""

import hashlib

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import *  # noqa: F401,F403
from app.infrastructure.database.models import (
    Customer,
    Formula,
    FormulaItem,
    ImportBatch,
    ImportStagingRecord,
    Material,
    Product,
)


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
    ws.append(["2025-01-01", "客户A", "产品X", "B001", "物料2", 5.0])
    ws.append(["2025-01-02", "客户B", "产品Y", "B002", "物料3", 20.0])
    path = tmp_path / "confirm_test.xlsx"
    wb.save(path)
    return str(path)


@pytest.fixture()
def patch_session(monkeypatch, db_session):
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
    imports_dir = tmp_path / "history_imports"
    imports_dir.mkdir()
    monkeypatch.setattr(
        "app.application.import_service.HISTORY_IMPORTS_DIR", imports_dir
    )
    return imports_dir


def _make_parsed_batch(db_session):
    """Create a PARSED batch with staging records directly in the DB."""
    batch = ImportBatch(
        batch_no="IMP_TEST_001",
        source_file_path="/tmp/test.xlsx",
        source_file_name="test.xlsx",
        file_hash="abc123",
        import_profile="type_a_flat",
        status="PARSED",
        total_rows=3,
    )
    db_session.add(batch)
    db_session.flush()

    rows = [
        {"customer": "客户A", "product": "产品X", "color": None, "batch_no": "B001", "material_name": "物料1", "usage": 10.5, "unit": "kg", "date": "2025-01-01"},
        {"customer": "客户A", "product": "产品X", "color": None, "batch_no": "B001", "material_name": "物料2", "usage": 5.0, "unit": "kg", "date": "2025-01-01"},
        {"customer": "客户B", "product": "产品Y", "color": "红", "batch_no": "B002", "material_name": "物料3", "usage": 20.0, "unit": "kg", "date": "2025-01-02"},
    ]
    for i, row in enumerate(rows):
        rec = ImportStagingRecord(
            batch_id=batch.id,
            record_index=i,
            raw_payload_json=row,
            normalized_payload_json=row,
            is_valid=True,
            is_selected=True,
        )
        db_session.add(rec)

    db_session.flush()
    return batch


def test_confirm_creates_customers(patch_session, db_session):
    from app.application.import_service import ImportService

    batch = _make_parsed_batch(db_session)
    svc = ImportService()
    result = svc.confirm_and_import(batch.id)

    assert result.status == "IMPORTED"
    customers = db_session.query(Customer).all()
    names = {c.customer_name for c in customers}
    assert "客户A" in names
    assert "客户B" in names


def test_confirm_creates_products(patch_session, db_session):
    from app.application.import_service import ImportService

    batch = _make_parsed_batch(db_session)
    svc = ImportService()
    svc.confirm_and_import(batch.id)

    products = db_session.query(Product).all()
    names = {p.product_name for p in products}
    assert "产品X" in names
    assert "产品Y" in names

    # Check product linked to customer
    px = db_session.query(Product).filter_by(product_name="产品X").one()
    cust = db_session.query(Customer).filter_by(customer_name="客户A").one()
    assert px.customer_id == cust.id


def test_confirm_creates_materials(patch_session, db_session):
    from app.application.import_service import ImportService

    batch = _make_parsed_batch(db_session)
    svc = ImportService()
    svc.confirm_and_import(batch.id)

    materials = db_session.query(Material).all()
    names = {m.standard_name for m in materials}
    assert "物料1" in names
    assert "物料2" in names
    assert "物料3" in names


def test_confirm_creates_formulas(patch_session, db_session):
    from app.application.import_service import ImportService

    batch = _make_parsed_batch(db_session)
    svc = ImportService()
    svc.confirm_and_import(batch.id)

    formulas = db_session.query(Formula).all()
    assert len(formulas) == 2  # (客户A,产品X,B001) and (客户B,产品Y,B002)

    # Verify fingerprint
    for f in formulas:
        if f.color is None:
            expected = hashlib.md5(f"{f.customer.customer_name}:{f.product.product_name}:".encode()).hexdigest()
        else:
            expected = hashlib.md5(f"{f.customer.customer_name}:{f.product.product_name}:{f.color}".encode()).hexdigest()
        assert f.formula_fingerprint == expected

    # Verify formula items
    f1 = [f for f in formulas if f.color is None][0]
    assert len(f1.items) == 2
    item_materials = {item.material.standard_name for item in f1.items}
    assert item_materials == {"物料1", "物料2"}


def test_confirm_idempotent(patch_session, db_session):
    from app.application.import_service import ImportService

    batch = _make_parsed_batch(db_session)
    svc = ImportService()
    svc.confirm_and_import(batch.id)

    customers_before = db_session.query(Customer).count()
    products_before = db_session.query(Product).count()
    materials_before = db_session.query(Material).count()
    formulas_before = db_session.query(Formula).count()

    # Second import with same data — create a new batch
    batch2 = ImportBatch(
        batch_no="IMP_TEST_002",
        source_file_path="/tmp/test.xlsx",
        source_file_name="test.xlsx",
        file_hash="abc123",
        import_profile="type_a_flat",
        status="PARSED",
        total_rows=3,
    )
    db_session.add(batch2)
    db_session.flush()
    for i, row in enumerate([
        {"customer": "客户A", "product": "产品X", "color": None, "batch_no": "B001", "material_name": "物料1", "usage": 10.5, "unit": "kg", "date": "2025-01-01"},
        {"customer": "客户A", "product": "产品X", "color": None, "batch_no": "B001", "material_name": "物料2", "usage": 5.0, "unit": "kg", "date": "2025-01-01"},
        {"customer": "客户B", "product": "产品Y", "color": "红", "batch_no": "B002", "material_name": "物料3", "usage": 20.0, "unit": "kg", "date": "2025-01-02"},
    ]):
        rec = ImportStagingRecord(
            batch_id=batch2.id,
            record_index=i,
            raw_payload_json=row,
            normalized_payload_json=row,
            is_valid=True,
            is_selected=True,
        )
        db_session.add(rec)
    db_session.flush()

    svc.confirm_and_import(batch2.id)

    assert db_session.query(Customer).count() == customers_before
    assert db_session.query(Product).count() == products_before
    assert db_session.query(Material).count() == materials_before
    # New formulas should be created for the new batch (fingerprint-based dedup)
    # Actually with same fingerprint, we skip creating duplicates
    assert db_session.query(Formula).count() == formulas_before
