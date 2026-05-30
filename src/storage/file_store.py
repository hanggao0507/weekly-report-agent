from __future__ import annotations

import json
from pathlib import Path

from src.config.settings import Settings
from src.models import TeamWeeklyReport


class FileStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.output_dir = settings.resolve_path(settings.report.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def persist(self, run_id: str, report: TeamWeeklyReport) -> TeamWeeklyReport:
        stamp = report.generated_at.strftime("%Y%m%d-%H%M%S")
        markdown_path = self.output_dir / f"report-{stamp}-{run_id}.md"
        html_path = self.output_dir / f"report-{stamp}-{run_id}.html"
        json_path = self.output_dir / f"report-{stamp}-{run_id}.json"
        markdown_path.write_text(report.artifacts.markdown, encoding="utf-8")
        html_path.write_text(report.artifacts.html, encoding="utf-8")
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report.artifacts.markdown_path = str(markdown_path)
        report.artifacts.html_path = str(html_path)
        report.artifacts.json_path = str(json_path)
        return report
