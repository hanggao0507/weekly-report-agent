from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import get_scheduler_service, get_settings


def test_generate_report_and_download_artifacts():
    app = create_app()
    with TestClient(app) as client:
        partial = client.get("/partials/home-status")
        assert partial.status_code == 200
        assert "最新结果" in partial.text

        response = client.post("/reports/generate", follow_redirects=False)
        assert response.status_code == 303
        location = response.headers["location"]

        detail = client.get(location)
        assert detail.status_code == 200
        assert "成员卡片" in detail.text
        assert "下载区" in detail.text
        assert "风险焦点" in detail.text

        run_id = location.rsplit("/", 1)[-1]
        status = client.get(f"/reports/{run_id}/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["status"] in {"completed", "completed_with_warnings"}

        md = client.get(f"/reports/{run_id}/download.md")
        html = client.get(f"/reports/{run_id}/download.html")
        preview = client.get(f"/reports/{run_id}/preview")
        assert md.status_code == 200
        assert html.status_code == 200
        assert preview.status_code == 200
        assert "团队总览" in md.text
        assert "<html" in html.text.lower()
        assert "团队总览" in preview.text


def test_scheduler_is_registered():
    app = create_app()
    scheduler = get_scheduler_service()
    with TestClient(app):
        next_run_time = scheduler.next_run_time()
        assert next_run_time is not None
        assert scheduler.scheduler.get_job("weekly-report-cron") is not None
