from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime

from src.config.settings import Settings
from src.models import ReportRun


class RunRepository:
    def __init__(self, settings: Settings):
        self.db_path = settings.resolve_path(settings.app.db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS report_runs (
                    run_id TEXT PRIMARY KEY,
                    trigger TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    window_label TEXT,
                    error_message TEXT,
                    markdown_path TEXT,
                    html_path TEXT,
                    warning_message TEXT
                )
                """
            )

    def create(self, trigger: str, created_at: datetime) -> ReportRun:
        run = ReportRun(
            run_id=uuid.uuid4().hex[:12],
            trigger=trigger,
            status="queued",
            created_at=created_at,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO report_runs (
                    run_id, trigger, status, created_at, started_at, finished_at,
                    window_label, error_message, markdown_path, html_path, warning_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.trigger,
                    run.status,
                    run.created_at.isoformat(),
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            )
        return run

    def mark_running(self, run_id: str, started_at: datetime) -> None:
        self._update(run_id, status="running", started_at=started_at.isoformat())

    def mark_completed(
        self,
        run_id: str,
        finished_at: datetime,
        status: str,
        window_label: str,
        markdown_path: str | None,
        html_path: str | None,
        warning_message: str | None,
    ) -> None:
        self._update(
            run_id,
            status=status,
            finished_at=finished_at.isoformat(),
            window_label=window_label,
            markdown_path=markdown_path,
            html_path=html_path,
            warning_message=warning_message,
        )

    def mark_failed(self, run_id: str, finished_at: datetime, error_message: str) -> None:
        self._update(run_id, status="failed", finished_at=finished_at.isoformat(), error_message=error_message)

    def _update(self, run_id: str, **fields: str | None) -> None:
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [run_id]
        with self._connect() as connection:
            connection.execute(f"UPDATE report_runs SET {assignments} WHERE run_id = ?", values)

    def get(self, run_id: str) -> ReportRun | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM report_runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_model(row) if row else None

    def latest(self) -> ReportRun | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM report_runs ORDER BY created_at DESC LIMIT 1").fetchone()
        return self._row_to_model(row) if row else None

    def find_running(self) -> ReportRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM report_runs WHERE status IN ('queued', 'running') ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return self._row_to_model(row) if row else None

    def list_runs(self, limit: int = 10) -> list[ReportRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM report_runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row: sqlite3.Row) -> ReportRun:
        def parse(value: str | None) -> datetime | None:
            return datetime.fromisoformat(value) if value else None

        return ReportRun(
            run_id=row["run_id"],
            trigger=row["trigger"],
            status=row["status"],
            created_at=parse(row["created_at"]),
            started_at=parse(row["started_at"]),
            finished_at=parse(row["finished_at"]),
            window_label=row["window_label"],
            error_message=row["error_message"],
            markdown_path=row["markdown_path"],
            html_path=row["html_path"],
            warning_message=row["warning_message"],
        )

