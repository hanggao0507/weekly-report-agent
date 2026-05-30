from __future__ import annotations

import argparse

from src.config import load_settings
from src.services import ReportService, RunService
from src.storage import RunRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a weekly report")
    parser.add_argument("--config", required=True, help="Path to YAML or JSON config")
    parser.add_argument("--trigger", default="manual", help="Run trigger label")
    args = parser.parse_args()

    settings = load_settings(args.config)
    repository = RunRepository(settings)
    report_service = ReportService(settings)
    run_service = RunService(settings, report_service, repository)
    run = run_service.start_run(trigger=args.trigger)
    print(f"Generated run {run.run_id} with status {run.status}")
    if run.markdown_path:
        print(f"Markdown: {run.markdown_path}")
    if run.html_path:
        print(f"HTML: {run.html_path}")


if __name__ == "__main__":
    main()

