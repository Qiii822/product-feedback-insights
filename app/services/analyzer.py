"""反馈理解（analyzer）：单条反馈 → 结构化分析。

决策（Phase 3）：analyzer 是一个薄薄的服务——构建 prompt → 调用 LLM（单次）
→ 校验结构化输出 → 组装完整的 FeedbackAnalysis。它不是自主 Agent，只是
"单次 LLM 调用 + 校验"的封装，符合 pipeline-first 原则。

系统字段（id / feedback_item_id / model / prompt_version / created_at）
由 analyzer 组装，不信任 LLM 输出中的这些字段，避免被模型注入污染。
"""

import uuid

from app.prompts.analysis import build_analysis_messages
from app.schemas.analysis import FeedbackAnalysis
from app.schemas.feedback import FeedbackItem
from app.services.interfaces import FeedbackAnalyzer, LLMClient


class LLMFeedbackAnalyzer(FeedbackAnalyzer):
    """基于 LLM 的反馈分析器（单次调用，结构化输出）。"""

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

    def analyze(self, item: FeedbackItem) -> FeedbackAnalysis:
        messages = build_analysis_messages(item)
        raw = self._llm.complete(messages, FeedbackAnalysis)

        # 校验：LLM 抽象已保证类型/枚举/范围，这里再兜底语义校验——
        # 系统绝不静默接受非法输出（如空 summary）。
        if not raw.summary.strip():
            raise ValueError("LLM 输出的 summary 为空，视为非法输出")

        return FeedbackAnalysis(
            id=uuid.uuid4().hex,
            feedback_item_id=item.id,
            summary=raw.summary,
            primary_category=raw.primary_category,
            issue_type=raw.issue_type,
            severity=raw.severity,
            entities=raw.entities,
            confidence=raw.confidence,
            needs_review=raw.needs_review,
            model=self._model,
            prompt_version=self._prompt_version,
        )
