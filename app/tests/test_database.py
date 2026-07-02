"""Tests for database models and session management."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import Customer, RecognitionJob
from app.infrastructure.database.models import *  # noqa: F401,F403 - register all models


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


EXPECTED_TABLES = {
    "recognition_jobs",
    "production_records",
    "record_material_items",
    "record_machine_params",
    "record_temperatures",
    "field_recognition_results",
    "field_candidates",
    "customers",
    "products",
    "materials",
    "material_aliases",
    "formulas",
    "formula_items",
    "manual_correction_logs",
    "import_batches",
    "import_staging_records",
    "import_staging_material_items",
    "import_staging_warnings",
    "mimo_request_logs",
    "mimo_cache",
}


def test_create_tables(db_engine):
    """All 20 table names must exist in metadata."""
    inspector = inspect(db_engine)
    actual = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - actual
    assert not missing, f"Missing tables: {missing}"


def test_create_recognition_job(db_session):
    """Create and persist a RecognitionJob row."""
    job = RecognitionJob(job_no="JOB-0001", status="UPLOADED")
    db_session.add(job)
    db_session.flush()

    assert job.id is not None
    fetched = db_session.get(RecognitionJob, job.id)
    assert fetched.job_no == "JOB-0001"
    assert fetched.status == "UPLOADED"


def test_create_customer(db_session):
    """Create and persist a Customer row."""
    customer = Customer(customer_code="C001", customer_name="Test Customer")
    db_session.add(customer)
    db_session.flush()

    assert customer.id is not None
    fetched = db_session.get(Customer, customer.id)
    assert fetched.customer_code == "C001"
    assert fetched.customer_name == "Test Customer"
