"""FastAPI 应用入口。

决策：使用"应用工厂"模式（create_app），把应用构造与启动分离，
便于测试（每个测试可得到独立实例）与后续注册更多路由/中间件。
"""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    setup_logging(settings.log_level)
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    return app


app = create_app()
