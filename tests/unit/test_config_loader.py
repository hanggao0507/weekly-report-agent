from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config import load_settings


def test_load_yaml_settings():
    settings = load_settings("config/example.yaml")
    assert settings.schedule.cron == "0 17 * * 5"
    assert settings.sources.github.mode == "mock"
    assert settings.resolve_path(settings.report.output_dir).name == "reports"


def test_load_json_settings(tmp_path: Path):
    config = {
        "schedule": {"cron": "0 17 * * 5", "timezone": "Asia/Shanghai"},
        "team": {"name": "Demo", "members_file": "./config/mock/team_members.json"},
        "sources": {
            "github": {"enabled": True, "mode": "mock", "mock_data_dir": "./config/mock/github", "repos": []},
            "feishu": {
                "enabled": True,
                "mode": "mock",
                "fixture_paths": {
                    "calendar": "./config/mock/feishu/calendar.json",
                    "messages": "./config/mock/feishu/messages.json",
                },
            },
        },
        "report": {"template": "default", "sections": ["done"], "output_dir": "./reports", "window_days": 7},
        "llm": {"mode": "mock", "provider": "rule-based", "model": "demo", "temperature": 0.0},
        "app": {"db_path": "./weekly_report.db", "host": "127.0.0.1", "port": 8000, "title": "Demo"},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    settings = load_settings(path)
    assert settings.team.name == "Demo"
    assert settings.sources.feishu.mode == "mock"


def test_invalid_window_days(tmp_path: Path):
    path = tmp_path / "invalid.yaml"
    path.write_text(
        """
schedule:
  cron: "0 17 * * 5"
  timezone: "Asia/Shanghai"
team:
  name: "Demo"
  members_file: "./config/mock/team_members.json"
sources:
  github:
    enabled: true
    mode: "mock"
    mock_data_dir: "./config/mock/github"
    repos: []
  feishu:
    enabled: true
    mode: "mock"
    fixture_paths:
      calendar: "./config/mock/feishu/calendar.json"
      messages: "./config/mock/feishu/messages.json"
report:
  template: "default"
  sections: ["done"]
  output_dir: "./reports"
  window_days: 0
llm:
  mode: "mock"
  provider: "rule-based"
  model: "demo"
  temperature: 0.0
app:
  db_path: "./weekly_report.db"
  host: "127.0.0.1"
  port: 8000
  title: "Demo"
        """,
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_settings(path)

