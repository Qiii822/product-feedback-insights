"""FeedbackItem 的 ORM 模型（数据库表 feedback_items）。

命名约定：ORM 模型加 `Model` 后缀（FeedbackItemModel），
以区别于 app/schemas 中的同名 Pydantic schema（FeedbackItem）。

Phase 2 字段与 schema 一一对应（固定字段，无自由 metadata）。
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class FeedbackItemModel(Base):
    __tablename__ = "feedback_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    feedback_id: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_segment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
