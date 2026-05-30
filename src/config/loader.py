from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from src.config.settings import Settings


def _read_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(handle) or {}
        elif path.suffix.lower() == ".json":
            data = json.load(handle)
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")
    if not isinstance(data, dict):
        raise ValueError("Config root must be an object")
    return data


def load_settings(config_path: str | Path | None = None) -> Settings:
    path_value = config_path or os.environ.get("WEEKLY_REPORT_CONFIG") or "config/example.yaml"
    path = Path(path_value).expanduser().resolve()
    raw = _read_config(path)
    return Settings.from_raw(raw, config_path=path)

