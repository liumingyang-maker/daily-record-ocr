"""Export service — assembles job data and delegates to Excel exporter."""

from app.infrastructure.database.models import (
    FieldRecognitionResult,
    ManualCorrectionLog,
    ProductionRecord,
    RecordMaterialItem,
    RecognitionJob,
)
from app.infrastructure.database.session import get_session
from app.infrastructure.excel.exporter import export_job_to_excel


class ExportService:
    def export_job(self, job_id: int) -> dict:
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
            record_ids = [r.id for r in records]

            materials = (
                session.query(RecordMaterialItem)
                .filter(RecordMaterialItem.record_id.in_(record_ids))
                .all()
            ) if record_ids else []

            field_results = (
                session.query(FieldRecognitionResult)
                .filter_by(job_id=job_id)
                .all()
            )

            corrections = (
                session.query(ManualCorrectionLog)
                .filter(ManualCorrectionLog.record_id.in_(record_ids))
                .all()
            ) if record_ids else []

            record_map = {r.id: r for r in records}
            customer_map = {}
            for r in records:
                if r.customer:
                    customer_map[r.id] = r.customer.customer_name
                else:
                    customer_map[r.id] = ""
            product_map = {}
            for r in records:
                if r.product:
                    product_map[r.id] = r.product.product_name
                else:
                    product_map[r.id] = ""

            data = {
                "job_no": job.job_no,
                "records": [
                    {
                        "记录号": r.record_index,
                        "时间": r.time_value or r.time_raw or "",
                        "客户": customer_map.get(r.id, ""),
                        "产品": product_map.get(r.id, ""),
                        "颜色": r.color_raw or "",
                        "牌号": r.date_batch_no_raw or "",
                    }
                    for r in records
                ],
                "materials": [
                    {
                        "记录号": record_map[m.record_id].record_index if m.record_id in record_map else "",
                        "序号": m.seq,
                        "物料名称": m.material_name_standard or m.material_name_raw or "",
                        "用量": m.usage_value,
                        "单位": m.unit_standard or m.unit_raw or "",
                        "置信度": m.confidence,
                    }
                    for m in materials
                ],
                "field_results": [
                    {
                        "记录号": record_map[fr.record_id].record_index if fr.record_id and fr.record_id in record_map else "",
                        "字段": fr.field_label or fr.field_key,
                        "OCR结果": fr.ocr_raw_text or "",
                        "MiMo结果": fr.mimo_raw_text or "",
                        "最终值": fr.final_value or "",
                        "置信度": fr.final_confidence,
                        "来源": fr.source or "",
                        "需确认": "是" if fr.need_review else "否",
                    }
                    for fr in field_results
                ],
                "corrections": [
                    {
                        "类型": c.correction_type,
                        "记录号": record_map[c.record_id].record_index if c.record_id in record_map else "",
                        "字段": c.field_key,
                        "旧值": c.old_value or "",
                        "新值": c.new_value or "",
                        "操作时间": c.created_at.isoformat() if c.created_at else "",
                    }
                    for c in corrections
                ],
            }

            out_path = export_job_to_excel(job_id, data)

            job.export_path = str(out_path)
            job.status = "EXPORTED"
            session.flush()

            return {"job_id": job_id, "job_no": job.job_no, "export_path": str(out_path)}
