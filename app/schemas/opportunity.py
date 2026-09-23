"""产品机会（ProductOpportunity）数据契约。

这是管线的最终输出：针对某个高优先级问题，生成可执行的建议。
evidence_refs 强制该建议"引用证据"，是后续度量幻觉率（hallucination rate）
的基础——输出必须能追溯到输入证据。
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ProductOpportunity(BaseModel):
    """一个产品机会建议。"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    product_problem_id: str | None = None
    title: str
    summary: str = ""
    recommendation: str  # 具体建议（诊断 + 第一步）
    expected_impact: str = ""  # 预期影响
    action_items: list[str] = Field(default_factory=list)  # 可执行修复/验证步骤（3~5 步）
    success_metrics: list[str] = Field(default_factory=list)  # 如何验证修复有效、支撑迭代
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence_refs: list[str] = Field(default_factory=list)  # 引用的 FeedbackItem.id
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
