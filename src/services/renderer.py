from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import markdown

from src.config.settings import Settings
from src.models import ReportArtifacts, TeamWeeklyReport


class ReportRenderer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.template_env = Environment(
            loader=FileSystemLoader(str(settings.resolve_path("./src/templates/report"))),
            autoescape=select_autoescape(enabled_extensions=("html",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, report: TeamWeeklyReport) -> ReportArtifacts:
        template = self.template_env.get_template(f"{self.settings.report.template}.md.j2")
        markdown_text = template.render(report=report, sections=self.settings.report.sections)
        html_body = markdown(markdown_text, extensions=["tables", "fenced_code"])
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Weekly Report</title>"
            "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;"
            "background:#f7f7f3;color:#1d2939}h1,h2,h3{color:#0f172a}code{background:#eef2f6;padding:0.1rem 0.3rem;"
            "border-radius:4px}blockquote{border-left:4px solid #0f766e;padding-left:1rem;color:#475467}"
            "table{border-collapse:collapse;width:100%}th,td{border:1px solid #d0d5dd;padding:0.5rem;text-align:left}"
            "</style></head><body>"
            f"{html_body}</body></html>"
        )
        return ReportArtifacts(markdown=markdown_text, html=html)

