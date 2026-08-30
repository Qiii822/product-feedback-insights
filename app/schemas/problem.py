"""产品问题（ProductProblem）数据契约。

置信度与内聚度是两个不同指标（不混用）：
- confidence：对该 Product Problem 的整体可信程度——当前为 provisional 占位
  （未校准，不用于产品决策），Phase 7 再设计校准（semantic coherence /
  similarity to centroid / category consistency / evidence quality / cluster size）。
- cohesion_score：簇内语义一致度（平均到质心的相似度），真实计算的确定性指标。
"""

import uuid

from pydantic import BaseModel, Field

from app.schemas.enums import PrimaryCategory, ProblemStatus, Severity


class ProductProblem(BaseModel):
    """一个产品问题（confirmed 或 candidate）。"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str  # 问题标题，如 "支付失败"
    description: str = ""  # 问题描述
    category: PrimaryCategory | None = None  # 问题分类（取簇内多数 primary_category）
    severity: Severity | None = None  # 严重程度
    affected_segments: list[str] = Field(default_factory=list)  # 受影响平台（从元数据聚合）
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)  # provisional 占位（未校准）
    cohesion_score: float = Field(ge=0.0, le=1.0, default=0.0)  # 簇内语义一致度
    status: ProblemStatus = ProblemStatus.CANDIDATE  # 处理阶段
    needs_review: bool = False  # 单成员候选 → True
    evidence_count: int = 0  # 支撑该问题的反馈条数
    priority_score: float = Field(default=0.0)  # 优先级得分（Phase 5 确定性打分）
