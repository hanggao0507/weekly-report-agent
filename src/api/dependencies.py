from __future__ import annotations

from functools import lru_cache

from src.config import load_settings
from src.scheduler import SchedulerService
from src.services import ReportService, RunService
from src.storage import RunRepository


@lru_cache(maxsize=1)
def get_settings():
    return load_settings()


@lru_cache(maxsize=1)
def get_report_service():
    return ReportService(get_settings())


@lru_cache(maxsize=1)
def get_run_repository():
    return RunRepository(get_settings())


@lru_cache(maxsize=1)
def get_run_service():
    return RunService(get_settings(), get_report_service(), get_run_repository())


@lru_cache(maxsize=1)
def get_scheduler_service():
    return SchedulerService(get_settings(), get_run_service())


def reset_dependencies() -> None:
    get_scheduler_service.cache_clear()
    get_run_service.cache_clear()
    get_run_repository.cache_clear()
    get_report_service.cache_clear()
    get_settings.cache_clear()
