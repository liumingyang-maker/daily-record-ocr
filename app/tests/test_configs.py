import pytest
from app.configs import load_config


def test_load_app_config():
    cfg = load_config("app")
    assert cfg["app"]["name"] == "每日生产记录智能识别系统"
    assert cfg["app"]["version"] == "0.1.0"
    assert cfg["app"]["port"] == 8765


def test_load_unit_rules():
    cfg = load_config("unit_rules")
    assert "g" in cfg["units"]
    assert cfg["units"]["g"]["conversion_to_kg"] == 0.001
    assert cfg["units"]["t"]["conversion_to_kg"] == 1000
    assert cfg["units"]["bag"]["conversion_to_kg"] is None


def test_load_template():
    cfg = load_config("template_daily_record_v1")
    template = cfg["template"]
    assert len(template["record_blocks"]) == 3
    assert template["canonical_size"]["width"] == 1800
    assert template["canonical_size"]["height"] == 2500
    assert len(template["header_fields"]) == 4
    assert len(template["temperature_fields"]) == 11


def test_load_nonexistent_config():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_xyz")
