"""机会生成（opportunity）：问题 + 证据 → 产品机会建议。

决策（Phase 5）：LLM 生成 title/summary/recommendation/expected_impact，
但必须 evidence-grounded；系统字段（id / product_problem_id / evidence_refs /
confidence）由 generator 组装，不信任 LLM。confidence 为 provisional 占位。
"""

import uuid

from app.prompts.opportunity import build_opportunity_messages
from app.schemas.evidence import Evidence
from app.schemas.opportunity import ProductOpportunity
from app.schemas.problem import ProductProblem
from app.services.interfaces import LLMClient, ProductOpportunityGenerator


class LLMOpportunityGenerator(ProductOpportunityGenerator):
    """基于 LLM 的机会生成器（单次调用，evidence-grounded）。"""

    def __init__(
        self,
        llm: LLMClient,
        *,
        model: str = "fake",
        prompt_version: str = "v1",
    ) -> None:
        self._llm = llm
        self._model = model
        self._prompt_version = prompt_version

    def generate(
        self,
        problem: ProductProblem,
        evidence: list[Evidence],
        texts: dict[str, str],
    ) -> ProductOpportunity:
        refs = [e.feedback_item_id for e in evidence if e.feedback_item_id]
        evidence_texts = [texts[rid] for rid in refs if rid in texts]

        messages = build_opportunity_messages(problem, evidence_texts)
        draft = self._llm.complete(messages, ProductOpportunity)

        if not draft.recommendation.strip():
            raise ValueError("LLM 输出的 recommendation 为空，视为非法输出")

        return ProductOpportunity(
            id=uuid.uuid4().hex,
            product_problem_id=problem.id,
            title=draft.title,
            summary=draft.summary,
            recommendation=draft.recommendation,
            expected_impact=draft.expected_impact,
            confidence=0.5,  # provisional 占位（未校准）
            evidence_refs=refs,
        )
