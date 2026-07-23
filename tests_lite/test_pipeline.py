import json

from lite_app.pipeline import extract_json, validate_result


def test_extract_json_from_code_fence():
    payload = extract_json('```json\n{"page_heading":"x","records":[],"warnings":[]}\n```')
    assert payload["page_heading"] == "x"


def test_validate_result_reports_path():
    schema = {
        "type": "object",
        "required": ["records"],
        "properties": {"records": {"type": "array"}},
    }
    errors = validate_result({"records": "wrong"}, schema)
    assert errors and errors[0].startswith("records:")
