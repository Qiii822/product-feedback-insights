"""InMemory 存储实现。

决策：Phase 1 提供 InMemoryFeedbackRepository（基于 dict 的列表存储），
用于测试与作为后续 SQLAlchemy 实现的参照。

真实数据库实现（SQLAlchemy 版 FeedbackRepository）在 Phase 2 落地，
配合 app/models 中的 ORM 模型。通过接口隔离，切换实现不影响上层。
"""

from app.schemas.feedback import FeedbackItem
from app.services.interfaces import FeedbackRepository


class InMemoryFeedbackRepository(FeedbackRepository):
    """进程内 dict 存储，进程结束后数据即失效（仅用于测试/演示）。"""

    def __init__(self) -> None:
        self._items: dict[str, FeedbackItem] = {}

    def add(self, items):
        for item in items:
            self._items[item.id] = item

    def get(self, item_id):
        return self._items.get(item_id)

    def list(self):
        return list(self._items.values())

    def get_existing_feedback_ids(self):
        return {item.feedback_id for item in self._items.values()}
