"""Unit tests for configuration loader."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from cascadeid.config.loader import load_settings, _deep_merge, _flatten_for_env


class TestDeepMerge:
    def test_scalar_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 99}

    def test_nested_merge(self):
        base = {"temporal": {"window_size_seconds": 86400, "history_windows": 30}}
        override = {"temporal": {"history_windows": 60}}
        result = _deep_merge(base, override)
        assert result["temporal"]["window_size_seconds"] == 86400
        assert result["temporal"]["history_windows"] == 60

    def test_base_not_mutated(self):
        base = {"a": {"x": 1}}
        override = {"a": {"x": 2}}
        _deep_merge(base, override)
        assert base["a"]["x"] == 1


class TestFlattenForEnv:
    def test_simple_flatten(self):
        data = {"temporal": {"window_size_seconds": 3600}}
        flat = _flatten_for_env(data)
        assert flat["TEMPORAL_WINDOW_SIZE_SECONDS"] == "3600"

    def test_list_preserved_as_string(self):
        data = {"candidates": {"strategies": ["a", "b"]}}
        flat = _flatten_for_env(data)
        assert "CANDIDATES_STRATEGIES" in flat


class TestLoadSettings:
    def test_load_with_temp_config(self, tmp_path):
        from cascadeid.config.settings import get_settings
        get_settings.cache_clear()

        base = {"temporal": {"window_size_seconds": 7200}}
        (tmp_path / "base.yaml").write_text(yaml.dump(base))
        (tmp_path / "test.yaml").write_text("")

        s = load_settings(env="test", config_dir=tmp_path)
        assert s.temporal.window_size_seconds == 7200