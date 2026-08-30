"""聚类演示入口：反馈 → 分析 → 聚类 → 持久化。

用法（在仓库根目录）：
    uv run python -m scripts.cluster
前置：先运行 scripts.ingest 摄取反馈。
"""

import sys

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.problem import SQLProblemRepository
from app.repositories.sql import SQLFeedbackRepository
from app.services.analyzer import LLMFeedbackAnalyzer
from app.services.clustering import EmbeddingClusteringService
from app.services.embedding import FastembedEmbeddingProvider
from app.services.llm import get_llm


def main() -> int:
    item_repo = SQLFeedbackRepository(SessionLocal)
    items = item_repo.list()
    if not items:
        print(
            "无反馈数据，请先运行："
            "uv run python -m scripts.ingest data/raw/sample_feedback.csv",
            file=sys.stderr,
        )
        return 1

    llm = get_llm()  # 有 DEEPSEEK_API_KEY 用 DeepSeek，否则回退 FakeLLM
    model = settings.deepseek_model if settings.deepseek_api_key else "fake"
    analyzer = LLMFeedbackAnalyzer(llm, model=model, prompt_version="v1")
    analyses = [analyzer.analyze(item) for item in items]

    embedder = FastembedEmbeddingProvider(model_name=settings.embedding_model)
    service = EmbeddingClusteringService(embedder, llm, threshold=settings.clustering_threshold)
    result = service.cluster(items, analyses)

    SQLProblemRepository(SessionLocal).save(result)

    text_by_id = {item.id: item.raw_text for item in items}
    confirmed = [p for p in result.problems if not p.needs_review]
    candidates = [p for p in result.problems if p.needs_review]
    print(f"\n聚类出 {len(result.problems)} 个问题（{len(confirmed)} confirmed / {len(candidates)} candidate），")
    print(f"other 条目（不参与聚类）：{result.other_count}（{result.other_percentage:.1f}%）\n")

    def _print_problem(p):
        category = p.category.value if p.category else "?"
        severity = p.severity.value if p.severity else "?"
        members = [e.feedback_item_id for e in result.evidence if e.product_problem_id == p.id]
        tag = "需复核" if p.needs_review else "已确认"
        print(f"■ {p.title}  [{category} / {severity}]  ({tag})")
        print(f"    证据 {p.evidence_count} 条 · cohesion {p.cohesion_score:.2f} · 平台 {p.affected_segments}")
        for mid in members:
            print(f"      - {text_by_id.get(mid, '?')}")

    for p in confirmed:
        _print_problem(p)
    if candidates:
        print("\n— Candidate（单条，需人工复核，不进入 ranking）：")
        for p in candidates:
            _print_problem(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
