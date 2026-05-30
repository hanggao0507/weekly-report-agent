from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SectionName = Literal["done", "in_progress", "risks", "next_week"]
RunStatus = Literal["queued", "running", "completed", "completed_with_warnings", "failed"]


class MemberProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    display_name: str
    github_logins: list[str] = Field(default_factory=list)
    github_emails: list[str] = Field(default_factory=list)
    feishu_user_id: str | None = None
    aliases: list[str] = Field(default_factory=list)


class TimeWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_at: datetime
    end_at: datetime
    timezone: str
    label: str


class NormalizedWorkItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    category: str
    member_id: str | None = None
    title: str
    status: str
    url: str | None = None
    timestamp: datetime
    evidence: str | None = None
    risk_flag: bool = False
    next_plan_hint: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class GeneratedSections(BaseModel):
    model_config = ConfigDict(extra="forbid")

    done: list[str] = Field(default_factory=list)
    in_progress: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_week: list[str] = Field(default_factory=list)


class MemberWeeklySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    display_name: str
    sections: GeneratedSections = Field(default_factory=GeneratedSections)
    raw_items: list[NormalizedWorkItem] = Field(default_factory=list)


class ReportArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown: str
    html: str
    markdown_path: str | None = None
    html_path: str | None = None
    json_path: str | None = None


class TeamWeeklyReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_name: str
    generated_at: datetime
    window: TimeWindow
    team_summary: GeneratedSections = Field(default_factory=GeneratedSections)
    member_summaries: list[MemberWeeklySummary] = Field(default_factory=list)
    unassigned_items: list[NormalizedWorkItem] = Field(default_factory=list)
    source_health: dict[str, str] = Field(default_factory=dict)
    artifacts: ReportArtifacts | None = None


class ReportRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    trigger: str
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    window_label: str | None = None
    error_message: str | None = None
    markdown_path: str | None = None
    html_path: str | None = None
    warning_message: str | None = None
