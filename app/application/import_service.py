"""Import service — staging暂存 for history record imports."""

import hashlib
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.infrastructure.database.models import (
    Customer,
    Formula,
    FormulaItem,
    ImportBatch,
    ImportStagingRecord,
    Material,
    Product,
)
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
                # Touch staging records so they're loaded before expunging
                _ = batch.staging_records
                for rec in batch.staging_records:
                    session.expunge(rec)
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

    def confirm_and_import(self, batch_id: int) -> ImportBatch:
        """Confirm import and write staging records to production tables.

        Auto-extracts: customers, products, materials, formulas, formula_items.
        """
        with get_session() as session:
            batch = session.get(ImportBatch, batch_id)
            if batch is None:
                raise ValueError(f"Batch {batch_id} not found")
            if batch.status != "PARSED":
                raise ValueError(
                    f"Batch {batch_id} status is {batch.status}, expected PARSED"
                )

            records = (
                session.query(ImportStagingRecord)
                .filter_by(batch_id=batch_id, is_valid=True, is_selected=True)
                .all()
            )

            # Group by (customer, product, color, batch_no) for formula creation
            groups = defaultdict(list)
            for rec in records:
                p = rec.normalized_payload_json
                key = (p.get("customer"), p.get("product"), p.get("color"), p.get("batch_no"))
                groups[key].append(rec)

            # Cache for get_or_create within this session
            customer_cache: dict[str, Customer] = {}
            product_cache: dict[tuple, Product] = {}
            material_cache: dict[str, Material] = {}

            for (cust_name, prod_name, color, _batch_no), group_records in groups.items():
                # get_or_create customer
                if cust_name in customer_cache:
                    customer = customer_cache[cust_name]
                else:
                    customer = (
                        session.query(Customer)
                        .filter_by(customer_name=cust_name)
                        .first()
                    )
                    if customer is None:
                        customer = Customer(customer_name=cust_name)
                        session.add(customer)
                        session.flush()
                    customer_cache[cust_name] = customer

                # get_or_create product (linked to customer)
                prod_key = (cust_name, prod_name)
                if prod_key in product_cache:
                    product = product_cache[prod_key]
                else:
                    product = (
                        session.query(Product)
                        .filter_by(customer_id=customer.id, product_name=prod_name)
                        .first()
                    )
                    if product is None:
                        product = Product(
                            customer_id=customer.id,
                            product_name=prod_name,
                            default_color=color,
                        )
                        session.add(product)
                        session.flush()
                    product_cache[prod_key] = product

                # get_or_create materials and build formula items
                formula_items_data = []
                for rec in group_records:
                    p = rec.normalized_payload_json
                    mat_name = p.get("material_name")
                    if mat_name in material_cache:
                        material = material_cache[mat_name]
                    else:
                        material = (
                            session.query(Material)
                            .filter_by(standard_name=mat_name)
                            .first()
                        )
                        if material is None:
                            material = Material(standard_name=mat_name)
                            session.add(material)
                            session.flush()
                        material_cache[mat_name] = material

                    formula_items_data.append({
                        "material_id": material.id,
                        "usage_value": p.get("usage"),
                        "unit_raw": p.get("unit"),
                        "unit_standard": p.get("unit"),
                    })

                # Create formula (dedup by fingerprint)
                fp_str = f"{cust_name}:{prod_name}:{color or ''}"
                fingerprint = hashlib.md5(fp_str.encode()).hexdigest()

                existing = (
                    session.query(Formula)
                    .filter_by(formula_fingerprint=fingerprint)
                    .first()
                )
                if existing is None:
                    formula = Formula(
                        customer_id=customer.id,
                        product_id=product.id,
                        color=color,
                        formula_name=f"{cust_name}/{prod_name}/{color or ''}",
                        formula_fingerprint=fingerprint,
                        created_from_import_batch_id=batch_id,
                    )
                    session.add(formula)
                    session.flush()

                    for seq, item_data in enumerate(formula_items_data):
                        fi = FormulaItem(
                            formula_id=formula.id,
                            seq=seq,
                            material_id=item_data["material_id"],
                            usage_value=item_data["usage_value"],
                            unit_raw=item_data["unit_raw"],
                            unit_standard=item_data["unit_standard"],
                        )
                        session.add(fi)

            batch.status = "IMPORTED"
            batch.confirmed_at = datetime.now()
            session.flush()
            session.refresh(batch)
            session.expunge(batch)
            return batch
