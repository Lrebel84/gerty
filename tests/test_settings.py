"""Tests for settings load/save and validation."""

import json
import tempfile
from pathlib import Path

import pytest

from gerty.config import DATA_DIR
from gerty.settings import DEFAULTS, load, save


@pytest.fixture
def temp_settings(monkeypatch):
    """Use a temp directory for settings during tests."""
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        monkeypatch.setattr("gerty.settings.SETTINGS_FILE", data_dir / "settings.json")
        monkeypatch.setattr("gerty.settings.DATA_DIR", data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        yield data_dir


def test_load_returns_defaults_when_no_file(temp_settings):
    result = load()
    assert "provider" in result
    assert result["provider"] == "local"
    assert "memory_enabled" in result
    assert result["memory_enabled"] is True


def test_save_and_load(temp_settings):
    save({"provider": "openrouter", "memory_enabled": False})
    result = load()
    assert result["provider"] == "openrouter"
    assert result["memory_enabled"] is False


def test_save_validates_provider(temp_settings):
    save({"provider": "invalid"})
    result = load()
    # Invalid value should be rejected; provider stays default
    assert result["provider"] in ("local", "openrouter")


def test_save_validates_memory_enabled(temp_settings):
    save({"memory_enabled": "not a bool"})
    result = load()
    assert isinstance(result["memory_enabled"], bool)


def test_save_partial_update(temp_settings):
    save({"provider": "openrouter"})
    result = load()
    assert result["provider"] == "openrouter"
    assert "local_model" in result
