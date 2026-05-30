from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from src.api.dependencies import get_run_service, get_scheduler_service, get_settings
from src.models import TeamWeeklyReport
from src.services.run_service import RunConflictError

router = APIRouter()


def _load_report_data(run) -> TeamWeeklyReport | None:
    candidate_paths: list[Path] = []
    if run.markdown_path:
        candidate_paths.append(Path(run.markdown_path).with_suffix(".json"))
    if run.html_path:
        candidate_paths.append(Path(run.html_path).with_suffix(".json"))

    for path in candidate_paths:
        if path.exists():
            return TeamWeeklyReport.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return None


def _build_dashboard(report: TeamWeeklyReport | None) -> dict:
    if report is None:
        return {
            "metrics": {},
            "top_risks": [],
            "top_next_steps": [],
            "top_done": [],
        }

    unique_risks = list(dict.fromkeys(report.team_summary.risks))
    unique_next_steps = list(dict.fromkeys(report.team_summary.next_week))
    unique_done = list(dict.fromkeys(report.team_summary.done))
    return {
        "metrics": {
            "member_count": len(report.member_summaries),
            "done_count": sum(len(member.sections.done) for member in report.member_summaries),
            "in_progress_count": sum(len(member.sections.in_progress) for member in report.member_summaries),
            "risk_count": sum(len(member.sections.risks) for member in report.member_summaries),
            "next_week_count": sum(len(member.sections.next_week) for member in report.member_summaries),
            "unassigned_count": len(report.unassigned_items),
        },
        "top_risks": unique_risks[:6],
        "top_next_steps": unique_next_steps[:6],
        "top_done": unique_done[:6],
    }


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    run_service = get_run_service()
    scheduler = get_scheduler_service()
    latest = run_service.latest_run()
    runs = run_service.list_runs(limit=10)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "settings": get_settings(),
            "latest_run": latest,
            "runs": runs,
            "next_run_time": scheduler.next_run_time(),
        },
    )


@router.post("/reports/generate")
def generate_report(request: Request):
    try:
        run = get_run_service().start_run(trigger="manual")
    except RunConflictError as exc:
        if request.headers.get("HX-Request"):
            return HTMLResponse(f"<div class='notice warning'>{exc}</div>", status_code=409)
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if request.headers.get("HX-Request"):
        latest = get_run_service().latest_run()
        runs = get_run_service().list_runs(limit=10)
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="partials/generate_result.html",
            context={
                "request": request,
                "run": run,
                "latest_run": latest,
                "runs": runs,
            },
        )
    return RedirectResponse(url=f"/reports/{run.run_id}", status_code=303)


@router.get("/reports/{run_id}", response_class=HTMLResponse)
def report_detail(request: Request, run_id: str):
    run = get_run_service().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    markdown_content = ""
    if run.markdown_path and Path(run.markdown_path).exists():
        markdown_content = Path(run.markdown_path).read_text(encoding="utf-8")
    report = _load_report_data(run)
    dashboard = _build_dashboard(report)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="report_detail.html",
        context={
            "request": request,
            "run": run,
            "report": report,
            "dashboard": dashboard,
            "markdown_content": markdown_content,
        },
    )


@router.get("/reports/{run_id}/status")
def report_status(run_id: str):
    run = get_run_service().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse(run.model_dump(mode="json"))


@router.get("/reports/{run_id}/download.md")
def download_markdown(run_id: str):
    run = get_run_service().get_run(run_id)
    if run is None or not run.markdown_path:
        raise HTTPException(status_code=404, detail="Markdown artifact not found")
    return FileResponse(run.markdown_path, media_type="text/markdown", filename=Path(run.markdown_path).name)


@router.get("/reports/{run_id}/download.html")
def download_html(run_id: str):
    run = get_run_service().get_run(run_id)
    if run is None or not run.html_path:
        raise HTTPException(status_code=404, detail="HTML artifact not found")
    return FileResponse(run.html_path, media_type="text/html", filename=Path(run.html_path).name)


@router.get("/reports/{run_id}/preview", response_class=HTMLResponse)
def preview_html(run_id: str):
    run = get_run_service().get_run(run_id)
    if run is None or not run.html_path:
        raise HTTPException(status_code=404, detail="HTML preview not found")
    html_path = Path(run.html_path)
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="HTML preview not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@router.get("/health")
def health():
    return {"status": "ok"}
