from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import Settings
from src.services.run_service import RunConflictError, RunService


class SchedulerService:
    def __init__(self, settings: Settings, run_service: RunService):
        self.settings = settings
        self.run_service = run_service
        self.scheduler = BackgroundScheduler(timezone=settings.schedule.timezone)

    def start(self) -> None:
        trigger = CronTrigger.from_crontab(self.settings.schedule.cron, timezone=self.settings.schedule.timezone)
        self.scheduler.add_job(self._safe_generate, trigger=trigger, id="weekly-report-cron", replace_existing=True)
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def next_run_time(self):
        job = self.scheduler.get_job("weekly-report-cron")
        return job.next_run_time if job else None

    def _safe_generate(self) -> None:
        try:
            self.run_service.start_run(trigger="schedule")
        except RunConflictError:
            return

