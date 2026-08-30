"""反馈理解（FeedbackAnalysis）数据契约。

这是"反馈理解"阶段的输出：一条反馈 → 一条结构化分析。
它是 LLM 结构化输出的核心契约（Phase 3 实现分析逻辑）。

分析维度与 docs/product/category-taxonomy.md 一致：
primary_category / issue_type / severity / confidence / needs_review
彼此独立；primary_category 不承载 severity / issue_type / root cause / priority。

注意：此 schema 不含 affected_segment——用户群体/平台不由 LLM 从单条
反馈推断，而是在 Phase 4/5 通过 Cluster → feedback IDs → FeedbackItem.platform
元数据计算真实分布。
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas.enums import IssueType, PrimaryCategory, Severity


class FeedbackAnalysis(BaseModel):
    """单条反馈的结构化分析结果。"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    feedback_item_id: str | None = None  # 关联的 FeedbackItem.id
    summary: str  # 一句话摘要
    primary_category: PrimaryCategory  # 问题分类（11 类）
    issue_type: IssueType  # 反馈类型（problem / request / question / feedback）
    severity: Severity  # 严重程度（序数）
    entities: list[str] = Field(default_factory=list)  # 抽取的实体，如 ["Apple Pay"]
    confidence: float = Field(ge=0.0, le=1.0)  # 本次理解的置信度
    needs_review: bool = False  # 多问题 / 难取舍时置 True，交由人工复核
    model: str | None = None  # 产生本结果的模型（可追溯）
    prompt_version: str | None = None  # 使用的 prompt 版本（可追溯）
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
