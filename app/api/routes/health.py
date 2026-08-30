"""健康检查端点。

决策：/health 不依赖数据库或其他外部资源，保持轻量、快速，
用于确认应用已启动（而非确认所有依赖都健康）。
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
