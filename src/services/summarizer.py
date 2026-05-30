from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.config.settings import Settings
from src.models import GeneratedSections, MemberWeeklySummary, NormalizedWorkItem, TeamWeeklyReport


SOURCE_LABELS = {
    "github": "Git 代码",
    "feishu": "飞书协同",
}

CATEGORY_LABELS = {
    "commit": "提交",
    "pull_request": "合并请求",
    "issue": "问题",
    "calendar": "日程",
    "message": "消息",
}


def _format_item(item: NormalizedWorkItem) -> str:
    source_label = SOURCE_LABELS.get(item.source, item.source)
    category_label = CATEGORY_LABELS.get(item.category, item.category)
    prefix = f"[{source_label}/{category_label}]"
    suffix = f" ({item.evidence})" if item.evidence else ""
    return f"{prefix} {item.title}{suffix}"


class BaseSummarizer(ABC):
    @abstractmethod
    def generate(
        self,
        team_name: str,
        report: TeamWeeklyReport,
        member_items: dict[str, list[NormalizedWorkItem]],
        display_names: dict[str, str],
    ) -> TeamWeeklyReport:
        raise NotImplementedError


class RuleBasedSummarizer(BaseSummarizer):
    def generate(
        self,
        team_name: str,
        report: TeamWeeklyReport,
        member_items: dict[str, list[NormalizedWorkItem]],
        display_names: dict[str, str],
    ) -> TeamWeeklyReport:
        member_summaries: list[MemberWeeklySummary] = []
        team_sections = GeneratedSections()

        for member_id, items in member_items.items():
            sections = GeneratedSections()
            next_plan_seen: set[str] = set()
            for item in sorted(items, key=lambda entry: entry.timestamp):
                text = _format_item(item)
                if item.status == "done":
                    sections.done.append(text)
                    team_sections.done.append(f"{display_names[member_id]}：{text}")
                elif item.status == "next_week":
                    sections.next_week.append(text)
                    team_sections.next_week.append(f"{display_names[member_id]}：{text}")
                else:
                    sections.in_progress.append(text)
                    team_sections.in_progress.append(f"{display_names[member_id]}：{text}")

                if item.risk_flag:
                    risk_text = item.raw.get("risk_hint") or text
                    sections.risks.append(risk_text)
                    team_sections.risks.append(f"{display_names[member_id]}：{risk_text}")

                if item.next_plan_hint and item.next_plan_hint not in next_plan_seen:
                    sections.next_week.append(item.next_plan_hint)
                    team_sections.next_week.append(f"{display_names[member_id]}：{item.next_plan_hint}")
                    next_plan_seen.add(item.next_plan_hint)

            member_summaries.append(
                MemberWeeklySummary(
                    member_id=member_id,
                    display_name=display_names[member_id],
                    sections=sections,
                    raw_items=sorted(items, key=lambda entry: entry.timestamp),
                )
            )

        report.team_name = team_name
        report.team_summary = team_sections
        report.member_summaries = sorted(member_summaries, key=lambda entry: entry.display_name)
        return report


class LLMSummarizer(BaseSummarizer):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.fallback = RuleBasedSummarizer()
        api_key = None
        if settings.llm.api_key_env:
            api_key = os.environ.get(settings.llm.api_key_env)
        self.client = (
            OpenAI(
                api_key=api_key,
                base_url=settings.llm.base_url,
                timeout=settings.llm.timeout_seconds,
                max_retries=settings.llm.max_retries,
            )
            if api_key
            else None
        )
        self.prompt_template = self._load_prompt_template()

    def generate(
        self,
        team_name: str,
        report: TeamWeeklyReport,
        member_items: dict[str, list[NormalizedWorkItem]],
        display_names: dict[str, str],
    ) -> TeamWeeklyReport:
        if self.client is None:
            raise ValueError(
                f"llm.mode=real 需要提供环境变量 {self.settings.llm.api_key_env or 'OPENAI_API_KEY'} 对应的 API Key"
            )

        raw_payload = self._serialize(member_items, display_names)
        prompt = self._build_prompt(team_name=team_name, window_label=report.window.label, raw_payload=raw_payload)
        try:
            response = self.client.responses.create(
                model=self.settings.llm.model,
                temperature=self.settings.llm.temperature,
                input=prompt,
            )
            parsed = self._parse_response(response.output_text)
            return self._apply_summary(report, parsed, member_items, display_names)
        except Exception:
            if self.settings.llm.fallback_to_mock:
                return self.fallback.generate(team_name, report, member_items, display_names)
            raise

    def _load_prompt_template(self) -> str:
        path = self.settings.resolve_path(self.settings.llm.prompt_template)
        return Path(path).read_text(encoding="utf-8")

    def _serialize(self, member_items: dict[str, list[NormalizedWorkItem]], display_names: dict[str, str]) -> str:
        payload: dict[str, Any] = {"members": []}
        for member_id, items in member_items.items():
            payload["members"].append(
                {
                    "member_id": member_id,
                    "display_name": display_names[member_id],
                    "items": [
                        {
                            "source": item.source,
                            "category": item.category,
                            "title": item.title,
                            "status": item.status,
                            "timestamp": item.timestamp.isoformat(),
                            "evidence": item.evidence,
                            "risk_flag": item.risk_flag,
                            "next_plan_hint": item.next_plan_hint,
                            "raw": item.raw,
                        }
                        for item in items
                    ],
                }
            )
        return json.dumps(payload, ensure_ascii=False)

    def _build_prompt(self, team_name: str, window_label: str, raw_payload: str) -> str:
        return self.prompt_template.format(team_name=team_name, window_label=window_label, raw_payload=raw_payload)

    def _parse_response(self, text: str) -> dict[str, Any]:
        normalized = text.strip()
        if normalized.startswith("```"):
            normalized = normalized.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(normalized)

    def _apply_summary(
        self,
        report: TeamWeeklyReport,
        parsed: dict[str, Any],
        member_items: dict[str, list[NormalizedWorkItem]],
        display_names: dict[str, str],
    ) -> TeamWeeklyReport:
        report.team_summary = GeneratedSections(**parsed.get("team_summary", {}))
        summaries: list[MemberWeeklySummary] = []
        for member in parsed.get("member_summaries", []):
            member_id = member["member_id"]
            summaries.append(
                MemberWeeklySummary(
                    member_id=member_id,
                    display_name=member.get("display_name", display_names.get(member_id, member_id)),
                    sections=GeneratedSections(
                        done=member.get("done", []),
                        in_progress=member.get("in_progress", []),
                        risks=member.get("risks", []),
                        next_week=member.get("next_week", []),
                    ),
                    raw_items=sorted(member_items.get(member_id, []), key=lambda entry: entry.timestamp),
                )
            )
        report.member_summaries = sorted(summaries, key=lambda entry: entry.display_name)
        return report


def build_summarizer(settings: Settings) -> BaseSummarizer:
    if settings.llm.mode == "real":
        return LLMSummarizer(settings)
    return RuleBasedSummarizer()
