from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScheduleSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cron: str = "0 17 * * 5"
    timezone: str = "Asia/Shanghai"


class TeamSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    members_file: str


class GitHubSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    mode: Literal["mock", "api"] = "mock"
    mock_data_dir: str
    repos: list[str] = Field(default_factory=list)
    token_env: str | None = None
    base_url: str | None = None


class FeishuFixturePaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calendar: str
    messages: str


class FeishuSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    mode: Literal["mock", "api"] = "mock"
    fixture_paths: FeishuFixturePaths
    app_id_env: str | None = None
    app_secret_env: str | None = None


class SourcesSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    github: GitHubSettings
    feishu: FeishuSettings


class ReportSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: str = "default"
    sections: list[str] = Field(default_factory=lambda: ["done", "in_progress", "risks", "next_week"])
    output_dir: str = "./reports"
    export_formats: list[str] = Field(default_factory=lambda: ["markdown", "html"])
    window_days: int = 7


class LLMSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["mock", "real"] = "mock"
    provider: str = "rule-based"
    model: str = "weekly-report-template"
    temperature: float = 0.0
    api_key_env: str | None = None
    base_url: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 2
    fallback_to_mock: bool = True
    prompt_template: str = "./src/templates/prompts/weekly_report_summary.txt"


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    db_path: str = "./weekly_report.db"
    host: str = "127.0.0.1"
    port: int = 8000
    title: str = "Weekly Report Agent"


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule: ScheduleSettings
    team: TeamSettings
    sources: SourcesSettings
    report: ReportSettings
    llm: LLMSettings
    app: AppSettings
    config_path: Path | None = None
    project_root: Path | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any], config_path: Path) -> "Settings":
        instance = cls(**raw)
        object.__setattr__(instance, "config_path", config_path)
        object.__setattr__(instance, "project_root", config_path.parent.parent.resolve())
        return instance

    @model_validator(mode="after")
    def validate_window(self) -> "Settings":
        if self.report.window_days <= 0:
            raise ValueError("report.window_days must be positive")
        return self

    def resolve_path(self, path_value: str) -> Path:
        path = Path(path_value).expanduser()
        if path.is_absolute():
            return path
        if self.project_root is None:
            return path.resolve()
        return (self.project_root / path).resolve()
