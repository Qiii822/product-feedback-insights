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
from app.services.diagnosis import LLMDiagnosisGenerator
from app.services.embedding import FastembedEmbeddingProvider
from app.services.issue_metrics import compute_facts, compute_issue_metrics
from app.services.llm import get_llm
from app.services.opportunity import LLMOpportunityGenerator
from app.services.prioritisation import WeightedPrioritisationService

logger = logging.getLogger("pipeline")

# 诊断（FACT/HYPOTHESIS/UNKNOWN）生成到前 K 个 confirmed 问题
DIAGNOSIS_TOP_K = 3


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

    # 3. 排序（只排 confirmed；含增长因子的可解释打分）
    metrics = compute_issue_metrics(items, result.problems, result.evidence)
    growth = {pid: m["growth_norm"] for pid, m in metrics.items()}
    prioritiser = WeightedPrioritisationService()
    ranked = prioritiser.prioritize(result.problems, growth=growth)

    # 4. 建议 + 诊断（top confirmed）
    texts = {item.id: item.raw_text for item in items}
    opportunity = None
    diagnoses: dict[str, dict] = {}
    if ranked:
        generator = LLMOpportunityGenerator(llm)
        top = ranked[0]
        top_evidence = [e for e in result.evidence if e.product_problem_id == top.id]
        opportunity = generator.generate(top, top_evidence, texts)

        # 诊断（FACT 确定性 / HYPOTHESIS + UNKNOWN 由 LLM，evidence-grounded）
        diagnosis_gen = LLMDiagnosisGenerator(llm)
        for p in ranked[:DIAGNOSIS_TOP_K]:
            member_texts = [
                texts[e.feedback_item_id]
                for e in result.evidence
                if e.product_problem_id == p.id and e.feedback_item_id in texts
            ]
            d = diagnosis_gen.generate(p, member_texts)
            diagnoses[p.id] = {
                "facts": compute_facts(p, metrics[p.id]),
                "hypotheses": d.hypotheses,
                "unknowns": d.unknowns,
            }

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
        m = metrics.get(p.id, {})
        return {
            "id": p.id,
            "title": p.title,
            "description": p.description,
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
            "volume_pct": m.get("volume_pct", 0.0),
            "sentiment": m.get("sentiment", {}),
            "affected_versions": m.get("affected_versions", []),
            "trend": m.get("trend", {}),
            "priority_factors": prioritiser.factor_breakdown(p, growth.get(p.id, 0.5)),
            "diagnosis": diagnoses.get(p.id),
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
                "action_items": opportunity.action_items,
                "success_metrics": opportunity.success_metrics,
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
