"""
cascadeid.config.loader

Load and merge configuration from YAML files and environment variables.

Priority (highest → lowest):
  1. Environment variables
  2. Environment-specific YAML  (e.g. configs/development.yaml)
  3. Base YAML                  (configs/base.yaml)
  4. Pydantic defaults

Usage:
    from cascadeid.config.loader import load_settings
    settings = load_settings(env="development")
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from cascadeid.config.settings import Settings

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "configs"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file safely. Returns empty dict if file does not exist."""
    if not path.exists():
        logger.debug("Config file not found, skipping: %s", path)
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")
    return data


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override into base.
    Override values win for scalar conflicts.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _flatten_for_env(data: dict, prefix: str = "") -> dict[str, str]:
    """
    Flatten nested YAML dict into environment-variable-style keys.
    E.g. {"temporal": {"window_size_seconds": 3600}} →
         {"TEMPORAL_WINDOW_SIZE_SECONDS": "3600"}
    """
    result: dict[str, str] = {}
    for key, value in data.items():
        env_key = f"{prefix}{key.upper()}"
        if isinstance(value, dict):
            result.update(_flatten_for_env(value, prefix=f"{env_key}_"))
        elif isinstance(value, list):
            result[env_key] = str(value)
        else:
            result[env_key] = str(value)
    return result


def load_settings(
    env: str | None = None,
    config_dir: Path | None = None,
) -> Settings:
    """
    Build a Settings object by merging:
      1. configs/base.yaml
      2. configs/{env}.yaml  (if env is specified and file exists)
      3. Environment variables (always win)

    Args:
        env: Environment name (e.g. 'development', 'production').
             Defaults to CASCADEID_ENV environment variable or 'development'.
        config_dir: Override config directory (useful in tests).

    Returns:
        Fully resolved Settings instance.
    """
    env = env or os.getenv("CASCADEID_ENV", "development")
    cfg_dir = config_dir or _CONFIG_DIR

    base_data = _load_yaml(cfg_dir / "base.yaml")
    env_data = _load_yaml(cfg_dir / f"{env}.yaml")
    merged = _deep_merge(base_data, env_data)

    # Inject YAML values as env vars (only where not already set)
    flat = _flatten_for_env(merged)
    for k, v in flat.items():
        if k not in os.environ:
            os.environ[k] = v

    settings = Settings()
    logger.info("Configuration loaded: mode=%s env=%s", settings.mode, env)
    return settings