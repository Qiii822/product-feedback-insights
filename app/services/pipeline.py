"""完整 pipeline 编排（供 API / UI 调用）：分析 → 聚类 → 排序 → 建议 → 持久化。"""

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


def run_pipeline() -> dict:
    """运行完整 pipeline，返回可直接渲染的结果 dict。"""
    item_repo = SQLFeedbackRepository(SessionLocal)
    problem_repo = SQLProblemRepository(SessionLocal)
    items = item_repo.list()
    if not items:
        return {
            "feedback_count": 0,
            "problems": [],
            "candidates": [],
            "opportunity": None,
            "other": {"count": 0, "percentage": 0.0, "samples": []},
        }

    llm = get_llm()
    model = settings.deepseek_model if settings.deepseek_api_key else "fake"

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

    return {
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
