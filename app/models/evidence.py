"""Evidence 的 ORM 模型（数据库表 evidence）。"""

import uuid

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    product_problem_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    feedback_item_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    analysis_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)
