"""Pipeline API 端点（供前端 UI 调用）。"""

import os
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import SessionLocal
from app.evaluation.cases import split_status
from app.evaluation.runner import run_classification
from app.repositories.problem import SQLProblemRepository
from app.repositories.sql import SQLFeedbackRepository
from app.services.ingestion import IngestionService
from app.services.llm import get_llm
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api", tags=["pipeline"])


class IngestRequest(BaseModel):
    filename: str
    content: str


@router.post("/ingest")
def ingest(req: IngestRequest):
    """摄取 CSV/JSON 内容（前端读取文件后把内容作为文本发来）。"""
    suffix = Path(req.filename).suffix.lower()
    if suffix not in (".csv", ".json"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{suffix}")
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as tmp:
        tmp.write(req.content)
        path = tmp.name
    try:
        item_repo = SQLFeedbackRepository(SessionLocal)
        SQLProblemRepository(SessionLocal).clear()  # 清旧问题 / 证据 / 机会
        item_repo.clear()  # 清旧反馈，保证上传的文件是唯一数据源
        return IngestionService(item_repo).ingest_file(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"摄取失败：{exc}") from exc
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
    try:
        return run_pipeline()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析失败：{exc}") from exc


@router.post("/evaluate")
def evaluate(split: Literal["dev", "test"] = Query("dev")):
    """运行分类评估，返回 accuracy / F1 / per-category / reliability / needs_review 等指标。

    - split=dev：调参集（prompt 就是照着它调的，指标已饱和，仅作回归信号）。
    - split=test：留出集，用于报告泛化指标。该集需人工盲标后才存在；缺失时
      返回 `available=false` 的「待标注」占位，而不是报错。

    可用性检查刻意排在 `get_llm()` **之前**：留出集没标注这件事不需要（也不应）
    触碰 LLM——否则未配置 API key 时，连"还没标注"都看不到。
    """
    status = split_status(split)
    if not status["available"]:
        return {
            "split": split,
            "available": False,
            "reason": f"留出集尚未标注：评估集 {status['source']} 不存在",
            "pending": status["pending"],
        }
    try:
        llm = get_llm()
        model = settings.deepseek_model if settings.deepseek_api_key else "fake"
        return {**run_classification(llm, model=model, split=split), "available": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"评估失败：{exc}") from exc


@router.post("/load_sample")
def load_sample():
    """清空并重新载入内置模拟数据（data/raw/mock_feedback.csv），保证每次都是干净的 48 条。"""
    sample_file = Path(__file__).resolve().parents[3] / "data" / "raw" / "mock_feedback.csv"
    try:
        item_repo = SQLFeedbackRepository(SessionLocal)
        SQLProblemRepository(SessionLocal).clear()  # 清旧问题 / 证据 / 机会
        item_repo.clear()  # 清旧反馈
        return IngestionService(item_repo).ingest_file(sample_file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"载入示例失败：{exc}") from exc
