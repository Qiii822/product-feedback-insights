"""Pipeline API 端点（供前端 UI 调用）。"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.repositories.sql import SQLFeedbackRepository
from app.services.ingestion import IngestionService
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api", tags=["pipeline"])


class IngestRequest(BaseModel):
    filename: str
    content: str


@router.post("/ingest")
def ingest(req: IngestRequest):
    """摄取 CSV/JSON 内容（前端读取文件后把内容作为文本发来）。"""
    suffix = Path(req.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as tmp:
        tmp.write(req.content)
        path = tmp.name
    try:
        service = IngestionService(SQLFeedbackRepository(SessionLocal))
        return service.ingest_file(path)
    finally:
        os.unlink(path)


@router.get("/feedback")
def feedback():
    """列出已摄取的反馈条目。"""
    items = SQLFeedbackRepository(SessionLocal).list()
    return [
        {
            "id": i.id,
            "feedback_id": i.feedback_id,
            "raw_text": i.raw_text,
            "source": i.source,
            "platform": i.platform,
        }
        for i in items
    ]


@router.post("/run")
def run():
    """运行完整 pipeline，返回可渲染的结果。"""
    return run_pipeline()
