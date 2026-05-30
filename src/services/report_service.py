from __future__ import annotations

from datetime import datetime, timedelta
from typing import TypedDict
from zoneinfo import ZoneInfo

from langgraph.graph import END, START, StateGraph

from src.models import NormalizedWorkItem
from src.adapters import FeishuMockAdapter, GitHubMockAdapter
from src.config.settings import Settings
from src.models import TeamWeeklyReport, TimeWindow
from src.services.member_service import MemberDirectory
from src.services.renderer import ReportRenderer
from src.services.summarizer import build_summarizer
from src.storage.file_store import FileStore


class WorkflowState(TypedDict, total=False):
    run_id: str
    trigger: str
    window: TimeWindow
    report: TeamWeeklyReport
    github_items: list[NormalizedWorkItem]
    feishu_items: list[NormalizedWorkItem]
    normalized_items: list[NormalizedWorkItem]
    member_items: dict[str, list[NormalizedWorkItem]]
    unassigned_items: list[NormalizedWorkItem]
    source_health: dict[str, str]


class ReportService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.member_directory = MemberDirectory(settings)
        self.github_adapter = GitHubMockAdapter(settings)
        self.feishu_adapter = FeishuMockAdapter(settings)
        self.summarizer = build_summarizer(settings)
        self.renderer = ReportRenderer(settings)
        self.file_store = FileStore(settings)
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        graph = StateGraph(WorkflowState)
        graph.add_node("resolve_window", self._resolve_window)
        graph.add_node("fetch_github_mock", self._fetch_github_mock)
        graph.add_node("fetch_feishu_mock", self._fetch_feishu_mock)
        graph.add_node("normalize_items", self._normalize_items)
        graph.add_node("aggregate_member", self._aggregate_member)
        graph.add_node("aggregate_team", self._aggregate_team)
        graph.add_node("summarize_report", self._summarize_report)
        graph.add_node("render_artifacts", self._render_artifacts)
        graph.add_node("persist_run", self._persist_run)
        graph.add_edge(START, "resolve_window")
        graph.add_edge("resolve_window", "fetch_github_mock")
        graph.add_edge("fetch_github_mock", "fetch_feishu_mock")
        graph.add_edge("fetch_feishu_mock", "normalize_items")
        graph.add_edge("normalize_items", "aggregate_member")
        graph.add_edge("aggregate_member", "aggregate_team")
        graph.add_edge("aggregate_team", "summarize_report")
        graph.add_edge("summarize_report", "render_artifacts")
        graph.add_edge("render_artifacts", "persist_run")
        graph.add_edge("persist_run", END)
        return graph.compile()

    def generate_report(self, run_id: str, trigger: str) -> TeamWeeklyReport:
        state = self.workflow.invoke({"run_id": run_id, "trigger": trigger})
        return state["report"]

    def _resolve_window(self, state: dict) -> dict:
        tz = ZoneInfo(self.settings.schedule.timezone)
        end_at = datetime.now(tz=tz)
        start_at = end_at - timedelta(days=self.settings.report.window_days)
        window = TimeWindow(
            start_at=start_at,
            end_at=end_at,
            timezone=self.settings.schedule.timezone,
            label=f"{start_at:%Y-%m-%d} ~ {end_at:%Y-%m-%d}",
        )
        report = TeamWeeklyReport(
            team_name=self.settings.team.name,
            generated_at=end_at,
            window=window,
        )
        return {"window": window, "report": report}

    def _fetch_github_mock(self, state: dict) -> dict:
        window = state["window"]
        all_items = []
        for member in self.member_directory.all():
            all_items.extend(self.github_adapter.fetch(member, window))
        return {"github_items": all_items, "source_health": {"github": "ok"}}

    def _fetch_feishu_mock(self, state: dict) -> dict:
        window = state["window"]
        all_items = []
        for member in self.member_directory.all():
            all_items.extend(self.feishu_adapter.fetch(member, window))
        source_health = dict(state.get("source_health", {}))
        source_health["feishu"] = "ok"
        return {"feishu_items": all_items, "source_health": source_health}

    def _normalize_items(self, state: dict) -> dict:
        items = [*state.get("github_items", []), *state.get("feishu_items", [])]
        for item in items:
            item.member_id = self.member_directory.assign_member(item)
        return {"normalized_items": items}

    def _aggregate_member(self, state: dict) -> dict:
        member_items: dict[str, list] = {member.member_id: [] for member in self.member_directory.all()}
        unassigned = []
        for item in state["normalized_items"]:
            if item.member_id and item.member_id in member_items:
                member_items[item.member_id].append(item)
            else:
                unassigned.append(item)
        return {"member_items": member_items, "unassigned_items": unassigned}

    def _aggregate_team(self, state: dict) -> dict:
        report: TeamWeeklyReport = state["report"]
        report.unassigned_items = state["unassigned_items"]
        report.source_health = state.get("source_health", {})
        return {"report": report}

    def _summarize_report(self, state: dict) -> dict:
        report: TeamWeeklyReport = state["report"]
        display_names = {member.member_id: member.display_name for member in self.member_directory.all()}
        report = self.summarizer.generate(
            team_name=self.settings.team.name,
            report=report,
            member_items=state["member_items"],
            display_names=display_names,
        )
        return {"report": report}

    def _render_artifacts(self, state: dict) -> dict:
        report: TeamWeeklyReport = state["report"]
        report.artifacts = self.renderer.render(report)
        return {"report": report}

    def _persist_run(self, state: dict) -> dict:
        report: TeamWeeklyReport = state["report"]
        self.file_store.persist(state["run_id"], report)
        return {"report": report}
