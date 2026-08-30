"""证据（Evidence）数据契约。

表示"某条反馈支撑了某个产品问题"的关联关系，是问题可追溯的关键：
每个 ProductProblem 都应由一批 Evidence 支撑，而不是凭空生成。
"""

import uuid

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """一条反馈对某个产品问题的支撑证据。"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    product_problem_id: str | None = None
    feedback_item_id: str | None = None
    analysis_id: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0, default=1.0)  # 相关度
