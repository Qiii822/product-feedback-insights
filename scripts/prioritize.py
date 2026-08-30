"""优先级排序演示：问题 → 打分 → 排序 → 机会建议 → 持久化。

用法（在仓库根目录）：
    uv run python -m scripts.prioritize
前置：先运行 scripts.ingest 与 scripts.cluster。
"""

import sys

from app.db.session import SessionLocal
from app.repositories.problem import SQLProblemRepository
from app.repositories.sql import SQLFeedbackRepository
from app.services.llm import get_llm
from app.services.opportunity import LLMOpportunityGenerator
from app.services.prioritisation import WeightedPrioritisationService


def main() -> int:
    problem_repo = SQLProblemRepository(SessionLocal)
    item_repo = SQLFeedbackRepository(SessionLocal)

    problems = problem_repo.list_problems()
    if not problems:
        print("无产品问题，请先运行 scripts.cluster", file=sys.stderr)
        return 1

    # 1. 确定性优先级排序（只排 confirmed）
    ranked = WeightedPrioritisationService().prioritize(problems)
    problem_repo.update_priorities(ranked)

    # 2. 对 top 问题生成 evidence-backed 建议
    evidence = problem_repo.list_evidence()
    items = item_repo.list()
    texts = {item.id: item.raw_text for item in items}
    generator = LLMOpportunityGenerator(get_llm())  # 有 DEEPSEEK_API_KEY 用 DeepSeek

    print(f"\n已排序 {len(ranked)} 个 confirmed 问题（按 priority_score 降序）：\n")
    for i, p in enumerate(ranked, start=1):
        sev = p.severity.value if p.severity else "?"
        print(
            f"{i}. {p.title}  [{p.category.value if p.category else '?'} / {sev}] "
            f"· score {p.priority_score:.3f} · 证据 {p.evidence_count} · 平台 {p.affected_segments}"
        )

    if ranked:
        top = ranked[0]
        top_evidence = [e for e in evidence if e.product_problem_id == top.id]
        opp = generator.generate(top, top_evidence, texts)
        problem_repo.save_opportunity(opp)
        print(f"\n■ Top 问题机会建议：{opp.title}")
        print(f"    建议：{opp.recommendation}")
        print(f"    预期影响：{opp.expected_impact}")
        print(f"    引用证据 {len(opp.evidence_refs)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
