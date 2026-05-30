from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.config.settings import GitHubSettings, Settings
from src.models import MemberProfile, NormalizedWorkItem, TimeWindow


class GitHubMockAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config: GitHubSettings = settings.sources.github
        self.data_dir = settings.resolve_path(self.config.mock_data_dir)

    def fetch(
        self,
        member: MemberProfile | None,
        window: TimeWindow,
        source_config: object | None = None,
    ) -> list[NormalizedWorkItem]:
        items: list[NormalizedWorkItem] = []
        items.extend(self._load_commits(member, window))
        items.extend(self._load_pulls(member, window))
        items.extend(self._load_issues(member, window))
        return items

    def _read_json(self, name: str) -> list[dict]:
        path = self.data_dir / name
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _matches_member(self, payload: dict, member: MemberProfile | None) -> bool:
        if member is None:
            return True
        login = payload.get("author_login")
        email = payload.get("author_email")
        return login in member.github_logins or email in member.github_emails

    def _in_window(self, value: str | None, window: TimeWindow) -> bool:
        if not value:
            return False
        ts = datetime.fromisoformat(value)
        return window.start_at <= ts <= window.end_at

    def _load_commits(self, member: MemberProfile | None, window: TimeWindow) -> list[NormalizedWorkItem]:
        rows = self._read_json("commits.json")
        output: list[NormalizedWorkItem] = []
        for row in rows:
            if not self._matches_member(row, member):
                continue
            if not self._in_window(row.get("committed_at"), window):
                continue
            output.append(
                NormalizedWorkItem(
                    source="github",
                    category="commit",
                    title=row["message"],
                    status="done",
                    url=row.get("html_url"),
                    timestamp=datetime.fromisoformat(row["committed_at"]),
                    evidence=f"{row['repo']}#{row['sha']}",
                    raw=row,
                )
            )
        return output

    def _load_pulls(self, member: MemberProfile | None, window: TimeWindow) -> list[NormalizedWorkItem]:
        rows = self._read_json("pulls.json")
        output: list[NormalizedWorkItem] = []
        for row in rows:
            if not self._matches_member(row, member):
                continue
            timestamp_value = row.get("merged_at") or row.get("updated_at")
            if not self._in_window(timestamp_value, window):
                continue
            labels = {label.lower() for label in row.get("labels", [])}
            status = "done" if row.get("merged_at") else "in_progress"
            risk_flag = "blocked" in labels or "risk" in labels
            output.append(
                NormalizedWorkItem(
                    source="github",
                    category="pull_request",
                    title=row["title"],
                    status=status,
                    url=row.get("html_url"),
                    timestamp=datetime.fromisoformat(timestamp_value),
                    evidence=f"{row['repo']}#PR-{row['id']}",
                    risk_flag=risk_flag,
                    raw=row,
                )
            )
        return output

    def _load_issues(self, member: MemberProfile | None, window: TimeWindow) -> list[NormalizedWorkItem]:
        rows = self._read_json("issues.json")
        output: list[NormalizedWorkItem] = []
        for row in rows:
            if not self._matches_member(row, member):
                continue
            timestamp_value = row.get("closed_at") or row.get("updated_at")
            if not self._in_window(timestamp_value, window):
                continue
            labels = {label.lower() for label in row.get("labels", [])}
            status = "done" if row.get("closed_at") else "in_progress"
            risk_flag = "risk" in labels or "blocked" in labels
            output.append(
                NormalizedWorkItem(
                    source="github",
                    category="issue",
                    title=row["title"],
                    status=status,
                    url=row.get("html_url"),
                    timestamp=datetime.fromisoformat(timestamp_value),
                    evidence=f"{row['repo']}#ISSUE-{row['id']}",
                    risk_flag=risk_flag,
                    raw=row,
                )
            )
        return output

