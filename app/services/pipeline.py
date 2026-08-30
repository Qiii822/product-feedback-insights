"""完整 pipeline 编排（供 API / UI 调用）：分析 → 聚类 → 排序 → 建议 → 持久化。"""

import logging
import time
import uuid

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.problem import SQLProblemRepository
from app.repositories.sql import SQLFeedbackRepository
from app.services.analyzer import LLMFeedbackAnalyzer
from app.services.clustering import EmbeddingClusteringService
from app.services.embedding import FastembedEmbeddingProvider
from app.services.llm import get_llm
from app.services.opportunity import LLMOpportunityGenerator
from app.services.prioritisation import WeightedPrioritisationService

logger = logging.getLogger("pipeline")


def _with_run(response: dict, run_id: str, started: float, llm, model: str) -> dict:
    """给响应附上 run 元数据（run_id / 延迟 / token / model）。"""
    response["run"] = {
        "run_id": run_id,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "total_tokens": getattr(llm, "total_tokens", 0),
        "total_calls": getattr(llm, "total_calls", 0),
        "model": model,
    }
    return response


def run_pipeline() -> dict:
    """运行完整 pipeline，返回可直接渲染的结果 dict（含 run 元数据）。"""
    run_id = uuid.uuid4().hex
    started = time.perf_counter()

    item_repo = SQLFeedbackRepository(SessionLocal)
    problem_repo = SQLProblemRepository(SessionLocal)
    items = item_repo.list()
    llm = get_llm()
    model = settings.deepseek_model if settings.deepseek_api_key else "fake"

    if not items:
        return _with_run(
            {
                "feedback_count": 0,
                "problems": [],
                "candidates": [],
                "opportunity": None,
                "other": {"count": 0, "percentage": 0.0, "samples": []},
            },
            run_id, started, llm, model,
        )

    # 1. 分析
    analyzer = LLMFeedbackAnalyzer(llm, model=model, prompt_version="v1")
    analyses = [analyzer.analyze(item) for item in items]

    # 2. 聚类（category-aware）
    embedder = FastembedEmbeddingProvider(model_name=settings.embedding_model)
    clustering = EmbeddingClusteringService(embedder, llm, threshold=settings.clustering_threshold)
    result = clustering.cluster(items, analyses)

    # 3. 排序（只排 confirmed）
    ranked = WeightedPrioritisationService().prioritize(result.problems)

    # 4. 建议（top confirmed）
    opportunity = None
    if ranked:
        texts = {item.id: item.raw_text for item in items}
        generator = LLMOpportunityGenerator(llm)
        top = ranked[0]
        top_evidence = [e for e in result.evidence if e.product_problem_id == top.id]
        opportunity = generator.generate(top, top_evidence, texts)

    # 5. 持久化（清旧 + 存新，避免重复累积）
    problem_repo.clear()
    problem_repo.save(result)
    problem_repo.update_priorities(ranked)
    if opportunity:
        problem_repo.save_opportunity(opportunity)

    # 6. 组装响应
    texts = {item.id: item.raw_text for item in items}

    def _problem_dict(p, rank=None):
        members = [e.feedback_item_id for e in result.evidence if e.product_problem_id == p.id]
        return {
            "id": p.id,
            "title": p.title,
            "category": p.category.value if p.category else None,
            "severity": p.severity.value if p.severity else None,
            "evidence_count": p.evidence_count,
            "confidence": p.confidence,
            "cohesion": p.cohesion_score,
            "affected_segments": p.affected_segments,
            "needs_review": p.needs_review,
            "priority_score": p.priority_score,
            "rank": rank,
            "evidence": [texts[m] for m in members if m in texts],
        }

    response = {
        "feedback_count": len(items),
        "problems": [_problem_dict(p, i) for i, p in enumerate(ranked, start=1)],
        "candidates": [_problem_dict(p) for p in result.problems if p.needs_review],
        "opportunity": (
            {
                "title": opportunity.title,
                "summary": opportunity.summary,
                "recommendation": opportunity.recommendation,
                "expected_impact": opportunity.expected_impact,
                "evidence_count": len(opportunity.evidence_refs),
            }
            if opportunity
            else None
        ),
        "other": {
            "count": result.other_count,
            "percentage": result.other_percentage,
            "samples": result.other_samples,
        },
    }
    logger.info(
        "run %s: %d feedback -> %d problems / %d candidates, %.0fms, %d tokens",
        run_id, len(items), len(ranked), len(result.problems) - len(ranked),
        (time.perf_counter() - started) * 1000, getattr(llm, "total_tokens", 0),
    )
    return _with_run(response, run_id, started, llm, model)
