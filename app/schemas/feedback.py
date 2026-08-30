"""反馈条目（FeedbackItem）数据契约。

Phase 2 起采用**固定字段**（不再使用自由 metadata dict），
字段对应 CSV/JSON 摄取契约（见 data/raw/sample_feedback.csv 与决策日志）。

字段语义：
- id：系统内部主键（UUID）
- feedback_id：来源系统的反馈标识（CSV 必填，精确去重依据）
- raw_text：原始反馈文本（必填，已做基础归一化）
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex


class FeedbackItem(BaseModel):
    """单条原始客户反馈。"""

    id: str = Field(default_factory=_new_id)
    feedback_id: str  # 来源系统反馈标识（必填）
    raw_text: str  # 原始反馈文本（必填）
    source: str | None = None  # 来源：app_review / support_ticket / nps ...（未提供 → None；无法识别 → "unknown"）
    platform: str | None = None  # 平台：ios / android / web ...（同上）
    app_version: str | None = None  # 应用版本（自由文本，可空）
    customer_segment: str | None = None  # 客户分群：free / paid / premium ...（同上）
    rating: int | None = Field(default=None, ge=1, le=5)  # 评分 1~5，可空
    timestamp: datetime | None = None  # 来源时间戳，可空
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # 摄取时间
