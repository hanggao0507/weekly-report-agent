from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.dependencies import get_scheduler_service, get_settings
from src.api.routes import router


def create_app() -> FastAPI:
    settings = get_settings()
    static_dir = settings.resolve_path("./web/static")
    static_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        get_scheduler_service().start()
        try:
            yield
        finally:
            get_scheduler_service().shutdown()

    app = FastAPI(title=settings.app.title, lifespan=lifespan)
    app.include_router(router)
    app.state.templates = Jinja2Templates(directory=str(settings.resolve_path("./web/templates")))
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
