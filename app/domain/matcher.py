"""Domain matchers for material, customer, and product lookup."""

from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    Customer,
    Material,
    MaterialAlias,
    Product,
)


def _fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def match_material(name: str, session: Session) -> list[dict]:
    """Return candidate materials ranked by confidence."""
    if not name or not name.strip():
        return []

    name_stripped = name.strip()
    candidates: list[dict] = []

    # 1. Exact match on standard_name
    exact = (
        session.query(Material)
        .filter(Material.standard_name == name_stripped, Material.status == "ACTIVE")
        .all()
    )
    for m in exact:
        candidates.append(
            {"id": m.id, "name": m.standard_name, "confidence": 1.0, "source": "exact"}
        )

    # 2. Alias match
    aliases = (
        session.query(MaterialAlias)
        .filter(MaterialAlias.alias == name_stripped)
        .all()
    )
    for alias in aliases:
        mat = alias.material
        if mat and mat.status == "ACTIVE":
            conf = alias.confidence if alias.confidence else 0.9
            candidates.append(
                {
                    "id": mat.id,
                    "name": mat.standard_name,
                    "confidence": conf,
                    "source": "alias",
                }
            )

    # 3. Fuzzy match
    all_materials = (
        session.query(Material).filter(Material.status == "ACTIVE").all()
    )
    existing_ids = {c["id"] for c in candidates}
    for m in all_materials:
        if m.id in existing_ids:
            continue
        score = _fuzzy_score(name_stripped, m.standard_name)
        if score >= 0.6:
            candidates.append(
                {
                    "id": m.id,
                    "name": m.standard_name,
                    "confidence": round(score, 4),
                    "source": "fuzzy",
                }
            )

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    return candidates


def match_customer(name: str, session: Session) -> list[dict]:
    """Return candidate customers ranked by confidence."""
    if not name or not name.strip():
        return []

    name_stripped = name.strip()
    candidates: list[dict] = []

    # 1. Exact match on customer_name
    exact = (
        session.query(Customer)
        .filter(Customer.customer_name == name_stripped, Customer.status == "ACTIVE")
        .all()
    )
    for c in exact:
        candidates.append(
            {"id": c.id, "name": c.customer_name, "confidence": 1.0, "source": "exact"}
        )

    # 2. Alias match (aliases_json is a list of strings)
    all_customers = (
        session.query(Customer).filter(Customer.status == "ACTIVE").all()
    )
    existing_ids = {c["id"] for c in candidates}
    for cust in all_customers:
        if cust.id in existing_ids:
            continue
        aliases = cust.aliases_json or []
        if name_stripped in aliases:
            candidates.append(
                {
                    "id": cust.id,
                    "name": cust.customer_name,
                    "confidence": 0.9,
                    "source": "alias",
                }
            )

    # 3. Fuzzy match
    fuzzy_pool = (
        session.query(Customer).filter(Customer.status == "ACTIVE").all()
    )
    existing_ids = {c["id"] for c in candidates}
    for cust in fuzzy_pool:
        if cust.id in existing_ids:
            continue
        score = _fuzzy_score(name_stripped, cust.customer_name)
        if score >= 0.6:
            candidates.append(
                {
                    "id": cust.id,
                    "name": cust.customer_name,
                    "confidence": round(score, 4),
                    "source": "fuzzy",
                }
            )

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    return candidates


def match_product(
    name: str, session: Session, customer_id: int | None = None
) -> list[dict]:
    """Return candidate products ranked by confidence."""
    if not name or not name.strip():
        return []

    name_stripped = name.strip()
    candidates: list[dict] = []

    query = session.query(Product).filter(Product.status == "ACTIVE")
    if customer_id is not None:
        query = query.filter(Product.customer_id == customer_id)
    all_products = query.all()

    # 1. Exact match on product_name
    for p in all_products:
        if p.product_name == name_stripped:
            candidates.append(
                {
                    "id": p.id,
                    "name": p.product_name,
                    "confidence": 1.0,
                    "source": "exact",
                }
            )

    # 2. Alias match (aliases_json is a list of strings)
    existing_ids = {c["id"] for c in candidates}
    for p in all_products:
        if p.id in existing_ids:
            continue
        aliases = p.aliases_json or []
        if name_stripped in aliases:
            candidates.append(
                {
                    "id": p.id,
                    "name": p.product_name,
                    "confidence": 0.9,
                    "source": "alias",
                }
            )

    # 3. Fuzzy match
    existing_ids = {c["id"] for c in candidates}
    for p in all_products:
        if p.id in existing_ids:
            continue
        score = _fuzzy_score(name_stripped, p.product_name)
        if score >= 0.6:
            candidates.append(
                {
                    "id": p.id,
                    "name": p.product_name,
                    "confidence": round(score, 4),
                    "source": "fuzzy",
                }
            )

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    return candidates
