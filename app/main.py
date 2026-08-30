"""FastAPI 应用入口。

决策：使用"应用工厂"模式（create_app），把应用构造与启动分离。
前端为静态单页（app/static/），由 FastAPI 直接托管，无构建步骤。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.health import router as health_router
from app.api.routes.pipeline import router as pipeline_router
from app.core.config import settings
from app.core.logging import setup_logging

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    setup_logging(settings.log_level)
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(pipeline_router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
