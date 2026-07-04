"""Tests for settings service and API."""

import pytest
from pathlib import Path
from app.application.settings_service import read_env, write_env, get_settings, save_settings, SETTINGS_CONFIG


@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    """Create a temporary .env file for testing."""
    env_path = tmp_path / ".env"
    env_path.write_text("MIMO_API_KEY=test-key\nAPP_PORT=8765\n", encoding="utf-8")
    monkeypatch.setattr("app.application.settings_service.ENV_PATH", env_path)
    return env_path


def test_read_env(temp_env):
    env = read_env()
    assert env["MIMO_API_KEY"] == "test-key"
    assert env["APP_PORT"] == "8765"


def test_write_env_updates_existing(temp_env):
    write_env({"MIMO_API_KEY": "new-key"})
    env = read_env()
    assert env["MIMO_API_KEY"] == "new-key"
    assert env["APP_PORT"] == "8765"


def test_write_env_adds_new_key(temp_env):
    write_env({"MIMO_MODEL": "mimo-v2.5"})
    env = read_env()
    assert env["MIMO_MODEL"] == "mimo-v2.5"


def test_get_settings_returns_groups(temp_env):
    groups = get_settings()
    assert "MiMo API" in groups
    assert "应用设置" in groups
    assert any(s["key"] == "MIMO_API_KEY" for s in groups["MiMo API"])


def test_save_settings(temp_env):
    save_settings({"MIMO_API_KEY": "saved-key", "INVALID_KEY": "ignored"})
    env = read_env()
    assert env["MIMO_API_KEY"] == "saved-key"
    assert "INVALID_KEY" not in env
