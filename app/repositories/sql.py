"""SQLAlchemy 版 FeedbackRepository（持久化）。

决策：Repository 只做持久化与查询，去重逻辑在 IngestionService，
保持职责单一。ORM ↔ Pydantic 的映射内聚在本模块。
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.feedback import FeedbackItemModel
from app.schemas.feedback import FeedbackItem
from app.services.interfaces import FeedbackRepository


def _to_model(item: FeedbackItem) -> FeedbackItemModel:
    return FeedbackItemModel(
        id=item.id,
        feedback_id=item.feedback_id,
        raw_text=item.raw_text,
        source=item.source,
        platform=item.platform,
        app_version=item.app_version,
        customer_segment=item.customer_segment,
        rating=item.rating,
        timestamp=item.timestamp,
        created_at=item.created_at,
    )


def _to_schema(model: FeedbackItemModel) -> FeedbackItem:
    return FeedbackItem(
        id=model.id,
        feedback_id=model.feedback_id,
        raw_text=model.raw_text,
        source=model.source,
        platform=model.platform,
        app_version=model.app_version,
        customer_segment=model.customer_segment,
        rating=model.rating,
        timestamp=model.timestamp,
        created_at=model.created_at,
    )


class SQLFeedbackRepository(FeedbackRepository):
    """基于 SQLAlchemy 的持久化实现。"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def add(self, items):
        if not items:
            return
        with self._session_factory() as session:
            session.add_all([_to_model(it) for it in items])
            session.commit()

    def get(self, item_id):
        with self._session_factory() as session:
            model = session.get(FeedbackItemModel, item_id)
            return _to_schema(model) if model else None

    def list(self):
        with self._session_factory() as session:
            models = session.scalars(select(FeedbackItemModel)).all()
            return [_to_schema(m) for m in models]

    def get_existing_feedback_ids(self):
        with self._session_factory() as session:
            ids = session.scalars(select(FeedbackItemModel.feedback_id)).all()
            return set(ids)

    def clear(self):
        with self._session_factory() as session:
            session.execute(delete(FeedbackItemModel))
            session.commit()
