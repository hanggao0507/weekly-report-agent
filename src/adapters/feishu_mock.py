from __future__ import annotations

import json
from datetime import datetime

from src.config.settings import FeishuSettings, Settings
from src.models import MemberProfile, NormalizedWorkItem, TimeWindow


class FeishuMockAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config: FeishuSettings = settings.sources.feishu

    def fetch(
        self,
        member: MemberProfile | None,
        window: TimeWindow,
        source_config: object | None = None,
    ) -> list[NormalizedWorkItem]:
        items: list[NormalizedWorkItem] = []
        items.extend(self._load_calendar(member, window))
        items.extend(self._load_messages(member, window))
        return items

    def _read_json(self, path_value: str) -> list[dict]:
        path = self.settings.resolve_path(path_value)
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _member_match(self, identifier: str | None, name: str | None, member: MemberProfile | None) -> bool:
        if member is None:
            return True
        if identifier and identifier == member.feishu_user_id:
            return True
        aliases = {alias.lower() for alias in member.aliases}
        aliases.add(member.display_name.lower())
        return bool(name and name.lower() in aliases)

    def _in_window(self, value: str, window: TimeWindow) -> bool:
        ts = datetime.fromisoformat(value)
        return window.start_at <= ts <= window.end_at

    def _load_calendar(self, member: MemberProfile | None, window: TimeWindow) -> list[NormalizedWorkItem]:
        rows = self._read_json(self.config.fixture_paths.calendar)
        output: list[NormalizedWorkItem] = []
        for row in rows:
            if not self._member_match(row.get("owner_user_id"), row.get("owner_name"), member):
                continue
            if not self._in_window(row["start_time"], window):
                continue
            output.append(
                NormalizedWorkItem(
                    source="feishu",
                    category="calendar",
                    title=row["event_title"],
                    status="done" if row.get("status") == "completed" else "in_progress",
                    url=None,
                    timestamp=datetime.fromisoformat(row["start_time"]),
                    evidence=row.get("summary"),
                    risk_flag=bool(row.get("risk_hint")),
                    next_plan_hint=row.get("next_plan_hint"),
                    raw=row,
                )
            )
        return output

    def _load_messages(self, member: MemberProfile | None, window: TimeWindow) -> list[NormalizedWorkItem]:
        rows = self._read_json(self.config.fixture_paths.messages)
        output: list[NormalizedWorkItem] = []
        for row in rows:
            if not self._member_match(row.get("sender_user_id"), row.get("sender_name"), member):
                continue
            if not self._in_window(row["message_time"], window):
                continue
            section_hint = row.get("section_hint") or "in_progress"
            output.append(
                NormalizedWorkItem(
                    source="feishu",
                    category="message",
                    title=row["message_text"],
                    status=section_hint,
                    url=None,
                    timestamp=datetime.fromisoformat(row["message_time"]),
                    evidence=row["message_id"],
                    risk_flag=bool(row.get("risk_hint")),
                    next_plan_hint=row.get("next_plan_hint"),
                    raw=row,
                )
            )
        return output

