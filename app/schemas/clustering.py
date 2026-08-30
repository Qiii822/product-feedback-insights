"""聚类相关数据契约。"""

from pydantic import BaseModel, Field

from app.schemas.evidence import Evidence
from app.schemas.problem import ProductProblem


class ClusterNaming(BaseModel):
    """LLM 为聚类生成的名称（evidence-grounded）。"""

    title: str
    description: str = ""


class ClusteringResult(BaseModel):
    """一次聚类的完整结果。

    problems 同时包含 confirmed（多成员簇，needs_review=False）与
    candidate（单成员簇，needs_review=True）两类问题——单成员不再被静默丢弃。
    """

    problems: list[ProductProblem] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    other_count: int = 0  # primary_category=other 的条目数（不参与聚类）
    other_percentage: float = 0.0
    other_samples: list[str] = Field(default_factory=list)  # 代表性 raw_text
