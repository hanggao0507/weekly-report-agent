from __future__ import annotations

from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo

from src.config.settings import Settings
from src.models import ReportRun, TeamWeeklyReport
from src.services.report_service import ReportService
from src.storage.run_repository import RunRepository


class RunConflictError(RuntimeError):
    pass


class RunService:
    def __init__(self, settings: Settings, report_service: ReportService, repository: RunRepository):
        self.settings = settings
        self.report_service = report_service
        self.repository = repository
        self._lock = Lock()

    def start_run(self, trigger: str = "manual") -> ReportRun:
        with self._lock:
            active = self.repository.find_running()
            if active is not None:
                raise RunConflictError("A report generation task is already running.")
            tz = ZoneInfo(self.settings.schedule.timezone)
            run = self.repository.create(trigger=trigger, created_at=datetime.now(tz=tz))
            self.repository.mark_running(run.run_id, started_at=datetime.now(tz=tz))
            try:
                report = self.report_service.generate_report(run.run_id, trigger=trigger)
                warning = None
                status = "completed"
                if report.unassigned_items:
                    status = "completed_with_warnings"
                    warning = f"There are {len(report.unassigned_items)} unassigned work items."
                self.repository.mark_completed(
                    run_id=run.run_id,
                    finished_at=datetime.now(tz=tz),
                    status=status,
                    window_label=report.window.label,
                    markdown_path=report.artifacts.markdown_path if report.artifacts else None,
                    html_path=report.artifacts.html_path if report.artifacts else None,
                    warning_message=warning,
                )
            except Exception as exc:  # pragma: no cover - covered by integration failure path via repository state
                self.repository.mark_failed(run.run_id, finished_at=datetime.now(tz=tz), error_message=str(exc))
                raise
            return self.repository.get(run.run_id)

    def latest_run(self) -> ReportRun | None:
        return self.repository.latest()

    def get_run(self, run_id: str) -> ReportRun | None:
        return self.repository.get(run_id)

    def list_runs(self, limit: int = 10) -> list[ReportRun]:
        return self.repository.list_runs(limit=limit)

