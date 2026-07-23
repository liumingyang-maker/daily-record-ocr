from pathlib import Path

from openpyxl import load_workbook

from lite_app import exporter


def test_exporter_writes_nested_rows(tmp_path, monkeypatch):
    result = {
        "page_heading": "测试",
        "records": [
            {
                "record_date": "24.7.10",
                "title": "A",
                "materials": [{"name": "PA66", "amount": "60", "unit": "kg", "confidence": 1}],
                "process_parameters": [],
                "notes": "",
                "confidence": 1,
                "warnings": [],
            }
        ],
        "warnings": [],
    }

    class FakeSettings:
        export = {
            "excel": {
                "template_path": "",
                "output_name": "out.xlsx",
                "cells": [],
                "tables": [
                    {
                        "sheet": "配方明细",
                        "source": "records",
                        "expand": "materials",
                        "start_row": 1,
                        "include_header": True,
                        "columns": [
                            {"column": "A", "header": "序号", "value": "$parent_index"},
                            {"column": "B", "header": "名称", "value": "name"},
                        ],
                    }
                ],
            }
        }

        def resolve_path(self, value):
            return Path(value)

    job = {"id": "job", "status": "READY"}
    monkeypatch.setattr(exporter, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(exporter, "load_result", lambda job_id: result)
    monkeypatch.setattr(exporter, "job_dir", lambda job_id: tmp_path)
    monkeypatch.setattr(exporter, "load_job", lambda job_id: job)
    monkeypatch.setattr(exporter, "save_job", lambda value: None)

    path = exporter.export_job("job")
    workbook = load_workbook(path)
    worksheet = workbook["配方明细"]
    assert worksheet["A2"].value == 1
    assert worksheet["B2"].value == "PA66"
