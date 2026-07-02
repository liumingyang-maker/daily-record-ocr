from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.infrastructure.database.base import Base


# ── 1. RecognitionJob ────────────────────────────────────────────────────────
class RecognitionJob(Base):
    __tablename__ = "recognition_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_no = Column(String(64), unique=True, nullable=False, index=True)
    source_image_path = Column(String(512))
    corrected_image_path = Column(String(512))
    status = Column(
        String(20),
        nullable=False,
        default="UPLOADED",
        # UPLOADED / PREPROCESSING / RECOGNIZING / NEED_REVIEW / CONFIRMED / EXPORTED / FAILED
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    error_message = Column(Text)
    ocr_engine = Column(String(64))
    mimo_used = Column(Boolean, default=False)
    mimo_mode = Column(String(32))
    export_path = Column(String(512))

    records = relationship("ProductionRecord", back_populates="job", lazy="selectin")
    field_results = relationship(
        "FieldRecognitionResult", back_populates="job", lazy="selectin"
    )


# ── 2. ProductionRecord ─────────────────────────────────────────────────────
class ProductionRecord(Base):
    __tablename__ = "production_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("recognition_jobs.id"), nullable=False, index=True)
    record_index = Column(Integer)
    record_crop_path = Column(String(512))
    time_raw = Column(String(128))
    time_value = Column(String(32))
    customer_queue_raw = Column(String(256))
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    color_raw = Column(String(128))
    color_standard = Column(String(128))
    date_batch_no_raw = Column(String(128))
    remark_raw = Column(Text)
    review_status = Column(String(20), default="PENDING")  # PENDING / REVIEWING / CONFIRMED
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime)

    job = relationship("RecognitionJob", back_populates="records")
    customer = relationship("Customer", back_populates="records")
    product = relationship("Product", back_populates="records")
    material_items = relationship(
        "RecordMaterialItem", back_populates="record", lazy="selectin"
    )
    machine_params = relationship(
        "RecordMachineParams", back_populates="record", uselist=False, lazy="selectin"
    )
    temperatures = relationship(
        "RecordTemperatures", back_populates="record", uselist=False, lazy="selectin"
    )
    field_results = relationship(
        "FieldRecognitionResult", back_populates="record", lazy="selectin"
    )
    correction_logs = relationship(
        "ManualCorrectionLog", back_populates="record", lazy="selectin"
    )


# ── 3. RecordMaterialItem ───────────────────────────────────────────────────
class RecordMaterialItem(Base):
    __tablename__ = "record_material_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(
        Integer, ForeignKey("production_records.id"), nullable=False, index=True
    )
    seq = Column(Integer)
    material_name_raw = Column(String(256))
    material_id = Column(Integer, ForeignKey("materials.id"), index=True)
    material_name_standard = Column(String(256))
    usage_raw = Column(String(128))
    usage_value = Column(Float)
    unit_raw = Column(String(32))
    unit_standard = Column(String(32))
    base_quantity_kg = Column(Float)
    confidence = Column(Float)
    source = Column(String(64))
    is_manual_corrected = Column(Boolean, default=False)

    record = relationship("ProductionRecord", back_populates="material_items")
    material = relationship("Material", back_populates="record_items")


# ── 4. RecordMachineParams ──────────────────────────────────────────────────
class RecordMachineParams(Base):
    __tablename__ = "record_machine_params"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(
        Integer, ForeignKey("production_records.id"), nullable=False, unique=True
    )
    main_speed_raw = Column(String(128))
    main_speed_value = Column(Float)
    feeder_speed_raw = Column(String(128))
    feeder_speed_value = Column(Float)
    side_feeder_fiber_raw = Column(String(128))
    side_feeder_fiber_value = Column(Float)
    main_current_raw = Column(String(128))
    main_current_value = Column(Float)
    vacuum_raw = Column(String(128))
    vacuum_value = Column(Float)
    material_temperature_raw = Column(String(128))
    material_temperature_value = Column(Float)

    record = relationship("ProductionRecord", back_populates="machine_params")


# ── 5. RecordTemperatures ───────────────────────────────────────────────────
class RecordTemperatures(Base):
    __tablename__ = "record_temperatures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(
        Integer, ForeignKey("production_records.id"), nullable=False, unique=True
    )
    zone_1_raw = Column(String(64))
    zone_1_value = Column(Float)
    zone_2_raw = Column(String(64))
    zone_2_value = Column(Float)
    zone_3_raw = Column(String(64))
    zone_3_value = Column(Float)
    zone_4_raw = Column(String(64))
    zone_4_value = Column(Float)
    zone_5_raw = Column(String(64))
    zone_5_value = Column(Float)
    zone_6_raw = Column(String(64))
    zone_6_value = Column(Float)
    zone_7_raw = Column(String(64))
    zone_7_value = Column(Float)
    zone_8_raw = Column(String(64))
    zone_8_value = Column(Float)
    zone_9_raw = Column(String(64))
    zone_9_value = Column(Float)
    zone_10_raw = Column(String(64))
    zone_10_value = Column(Float)
    head_temperature_raw = Column(String(64))
    head_temperature_value = Column(Float)

    record = relationship("ProductionRecord", back_populates="temperatures")


# ── 6. FieldRecognitionResult ───────────────────────────────────────────────
class FieldRecognitionResult(Base):
    __tablename__ = "field_recognition_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("recognition_jobs.id"), nullable=False, index=True)
    record_id = Column(Integer, ForeignKey("production_records.id"), index=True)
    field_key = Column(String(64), nullable=False)
    field_label = Column(String(128))
    cell_crop_path = Column(String(512))
    ocr_raw_text = Column(Text)
    ocr_confidence = Column(Float)
    mimo_raw_text = Column(Text)
    mimo_confidence = Column(Float)
    history_suggested_value = Column(Text)
    history_confidence = Column(Float)
    final_value = Column(Text)
    final_confidence = Column(Float)
    source = Column(String(64))
    need_review = Column(Boolean, default=False)
    manual_value = Column(Text)
    manual_corrected = Column(Boolean, default=False)
    reason = Column(Text)
    warnings_json = Column(JSON)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    job = relationship("RecognitionJob", back_populates="field_results")
    record = relationship("ProductionRecord", back_populates="field_results")
    candidates = relationship(
        "FieldCandidate", back_populates="field_result", lazy="selectin"
    )


# ── 7. FieldCandidate ──────────────────────────────────────────────────────
class FieldCandidate(Base):
    __tablename__ = "field_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_result_id = Column(
        Integer,
        ForeignKey("field_recognition_results.id"),
        nullable=False,
        index=True,
    )
    candidate_value = Column(Text)
    source = Column(String(64))
    confidence = Column(Float)
    reason = Column(Text)
    rank = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    field_result = relationship("FieldRecognitionResult", back_populates="candidates")


# ── 8. Customer ─────────────────────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_code = Column(String(64), index=True)
    customer_name = Column(String(256), nullable=False)
    aliases_json = Column(JSON)
    status = Column(String(20), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    records = relationship("ProductionRecord", back_populates="customer")
    products = relationship("Product", back_populates="customer", lazy="selectin")
    formulas = relationship("Formula", back_populates="customer", lazy="selectin")


# ── 9. Product ──────────────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    product_code = Column(String(64), index=True)
    product_name = Column(String(256), nullable=False)
    aliases_json = Column(JSON)
    default_color = Column(String(128))
    status = Column(String(20), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", back_populates="products")
    records = relationship("ProductionRecord", back_populates="product")
    formulas = relationship("Formula", back_populates="product", lazy="selectin")


# ── 10. Material ────────────────────────────────────────────────────────────
class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(64), index=True)
    standard_name = Column(String(256), nullable=False)
    category = Column(String(128))
    aliases_json = Column(JSON)
    common_ocr_errors_json = Column(JSON)
    unit_default = Column(String(32))
    status = Column(String(20), default="ACTIVE")
    usage_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    record_items = relationship("RecordMaterialItem", back_populates="material")
    aliases = relationship("MaterialAlias", back_populates="material", lazy="selectin")
    formula_items = relationship("FormulaItem", back_populates="material", lazy="selectin")


# ── 11. MaterialAlias ──────────────────────────────────────────────────────
class MaterialAlias(Base):
    __tablename__ = "material_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    alias = Column(String(256), nullable=False)
    alias_type = Column(
        String(32),
        nullable=False,
        # MANUAL_ALIAS / HISTORY_ALIAS / OCR_ERROR / IMPORT_VARIANT
    )
    source = Column(String(64))
    confidence = Column(Float)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    material = relationship("Material", back_populates="aliases")


# ── 12. Formula ─────────────────────────────────────────────────────────────
class Formula(Base):
    __tablename__ = "formulas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    color = Column(String(128))
    formula_name = Column(String(256))
    formula_fingerprint = Column(String(128), index=True)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    status = Column(String(20), default="ACTIVE")
    created_from_record_id = Column(Integer, ForeignKey("production_records.id"))
    created_from_import_batch_id = Column(Integer, ForeignKey("import_batches.id"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", back_populates="formulas")
    product = relationship("Product", back_populates="formulas")
    items = relationship("FormulaItem", back_populates="formula", lazy="selectin")


# ── 13. FormulaItem ─────────────────────────────────────────────────────────
class FormulaItem(Base):
    __tablename__ = "formula_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    formula_id = Column(Integer, ForeignKey("formulas.id"), nullable=False, index=True)
    seq = Column(Integer)
    material_id = Column(Integer, ForeignKey("materials.id"), index=True)
    usage_value = Column(Float)
    unit_raw = Column(String(32))
    unit_standard = Column(String(32))
    base_quantity_kg = Column(Float)
    tolerance_percent = Column(Float)
    tolerance_absolute = Column(Float)

    formula = relationship("Formula", back_populates="items")
    material = relationship("Material", back_populates="formula_items")


# ── 14. ManualCorrectionLog ─────────────────────────────────────────────────
class ManualCorrectionLog(Base):
    __tablename__ = "manual_correction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(
        Integer, ForeignKey("production_records.id"), nullable=False, index=True
    )
    field_key = Column(String(64), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    operator = Column(String(64))
    correction_type = Column(
        String(32),
        nullable=False,
        # OCR_ERROR / MIMO_ERROR / HISTORY_MATCH_ERROR / NEW_MATERIAL /
        # NEW_CUSTOMER / UNIT_CORRECTION / OTHER
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    record = relationship("ProductionRecord", back_populates="correction_logs")


# ── 15. ImportBatch ─────────────────────────────────────────────────────────
class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_no = Column(String(64), unique=True, nullable=False, index=True)
    source_file_path = Column(String(512))
    source_file_name = Column(String(256))
    file_hash = Column(String(128))
    import_profile = Column(String(64))
    status = Column(
        String(20),
        nullable=False,
        default="UPLOADED",
        # UPLOADED / PARSING / PARSED / NEED_MAPPING / NEED_REVIEW / CONFIRMED / IMPORTED / FAILED
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime)
    total_rows = Column(Integer)
    valid_rows = Column(Integer)
    invalid_rows = Column(Integer)
    error_message = Column(Text)

    staging_records = relationship(
        "ImportStagingRecord", back_populates="batch", lazy="selectin"
    )
    staging_warnings = relationship(
        "ImportStagingWarning", back_populates="batch", lazy="selectin"
    )


# ── 16. ImportStagingRecord ─────────────────────────────────────────────────
class ImportStagingRecord(Base):
    __tablename__ = "import_staging_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(
        Integer, ForeignKey("import_batches.id"), nullable=False, index=True
    )
    source_sheet = Column(String(128))
    source_row_start = Column(Integer)
    record_index = Column(Integer)
    raw_payload_json = Column(JSON)
    normalized_payload_json = Column(JSON)
    validation_errors_json = Column(JSON)
    is_valid = Column(Boolean, default=True)
    is_selected = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    batch = relationship("ImportBatch", back_populates="staging_records")
    material_items = relationship(
        "ImportStagingMaterialItem", back_populates="staging_record", lazy="selectin"
    )
    warnings = relationship(
        "ImportStagingWarning", back_populates="staging_record", lazy="selectin"
    )


# ── 17. ImportStagingMaterialItem ───────────────────────────────────────────
class ImportStagingMaterialItem(Base):
    __tablename__ = "import_staging_material_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    staging_record_id = Column(
        Integer,
        ForeignKey("import_staging_records.id"),
        nullable=False,
        index=True,
    )
    seq = Column(Integer)
    material_name_raw = Column(String(256))
    material_name_clean = Column(String(256))
    usage_raw = Column(String(128))
    usage_value = Column(Float)
    unit_raw = Column(String(32))
    unit_standard = Column(String(32))
    base_quantity_kg = Column(Float)
    validation_status = Column(String(32))

    staging_record = relationship(
        "ImportStagingRecord", back_populates="material_items"
    )


# ── 18. ImportStagingWarning ────────────────────────────────────────────────
class ImportStagingWarning(Base):
    __tablename__ = "import_staging_warnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(
        Integer, ForeignKey("import_batches.id"), nullable=False, index=True
    )
    staging_record_id = Column(
        Integer, ForeignKey("import_staging_records.id"), index=True
    )
    level = Column(String(16), nullable=False)  # INFO / WARNING / ERROR
    field_key = Column(String(64))
    message = Column(Text)
    suggested_action = Column(Text)

    batch = relationship("ImportBatch", back_populates="staging_warnings")
    staging_record = relationship("ImportStagingRecord", back_populates="warnings")


# ── 19. MimoRequestLog ──────────────────────────────────────────────────────
class MimoRequestLog(Base):
    __tablename__ = "mimo_request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("recognition_jobs.id"), index=True)
    record_id = Column(Integer, index=True)
    request_type = Column(String(64))
    model = Column(String(128))
    prompt_version = Column(String(64))
    image_hash = Column(String(128), index=True)
    request_payload_hash = Column(String(128))
    response_json = Column(JSON)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ── 20. MimoCache ───────────────────────────────────────────────────────────
class MimoCache(Base):
    __tablename__ = "mimo_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_hash = Column(String(128), nullable=False, index=True)
    prompt_version = Column(String(64), nullable=False)
    model = Column(String(128), nullable=False)
    response_json = Column(JSON)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
