"""Tests for domain matchers."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.matcher import match_customer, match_material, match_product
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    Customer,
    Material,
    MaterialAlias,
    Product,
)


@pytest.fixture()
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def seeded_session(db_engine):
    with Session(db_engine) as session:
        # Materials
        mat = Material(
            standard_name="PE-LLD 7042", material_code="M001", status="ACTIVE"
        )
        session.add(mat)
        session.flush()
        alias = MaterialAlias(
            material_id=mat.id, alias="LLDPE 7042", alias_type="MANUAL_ALIAS", confidence=0.92
        )
        session.add(alias)

        # Customer
        cust = Customer(
            customer_name="Acme Corp",
            customer_code="C001",
            aliases_json=["ACME", "acme corporation"],
            status="ACTIVE",
        )
        session.add(cust)
        session.flush()

        # Product
        prod = Product(
            customer_id=cust.id,
            product_name="Film A",
            product_code="P001",
            aliases_json=["FILM-A"],
            status="ACTIVE",
        )
        session.add(prod)

        session.commit()
        yield session


def test_match_material_exact(seeded_session):
    results = match_material("PE-LLD 7042", seeded_session)
    assert any(r["source"] == "exact" and r["confidence"] == 1.0 for r in results)


def test_match_material_alias(seeded_session):
    results = match_material("LLDPE 7042", seeded_session)
    assert any(r["source"] == "alias" and r["id"] is not None for r in results)


def test_match_customer_exact(seeded_session):
    results = match_customer("Acme Corp", seeded_session)
    assert results[0]["source"] == "exact"
    assert results[0]["confidence"] == 1.0


def test_match_product_with_customer(seeded_session):
    cust = seeded_session.query(Customer).first()
    results = match_product("Film A", seeded_session, customer_id=cust.id)
    assert any(r["source"] == "exact" for r in results)


def test_match_empty_returns_empty(seeded_session):
    assert match_material("", seeded_session) == []
    assert match_customer("", seeded_session) == []
    assert match_product("", seeded_session) == []
