from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

import pytest
import yaml

from src.api.dependencies import reset_dependencies


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def configured_environment(tmp_path: Path):
    config_dir = PROJECT_ROOT / "config"
    base_config_path = config_dir / "example.yaml"
    with base_config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    run_suffix = uuid.uuid4().hex[:8]
    test_output_dir = PROJECT_ROOT / "test-output" / run_suffix
    test_output_dir.mkdir(parents=True, exist_ok=True)

    config["report"]["output_dir"] = f"./test-output/{run_suffix}/reports"
    config["app"]["db_path"] = f"./test-output/{run_suffix}/weekly_report.db"

    temp_config_path = config_dir / f"test-{run_suffix}.yaml"
    temp_config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")

    os.environ["WEEKLY_REPORT_CONFIG"] = str(temp_config_path)
    reset_dependencies()
    yield
    reset_dependencies()
    os.environ.pop("WEEKLY_REPORT_CONFIG", None)
    if temp_config_path.exists():
        temp_config_path.unlink()
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir, ignore_errors=True)
