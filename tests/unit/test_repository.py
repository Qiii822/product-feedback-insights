"""InMemoryFeedbackRepository 测试。"""

from app.repositories.memory import InMemoryFeedbackRepository
from app.schemas.feedback import FeedbackItem


def test_add_and_get():
    repo = InMemoryFeedbackRepository()
    item = FeedbackItem(feedback_id="fb_1", raw_text="Payment failed again.")
    repo.add([item])
    assert repo.get(item.id) is item


def test_list_returns_all_items():
    repo = InMemoryFeedbackRepository()
    items = [
        FeedbackItem(feedback_id="1", raw_text="a"),
        FeedbackItem(feedback_id="2", raw_text="b"),
    ]
    repo.add(items)
    assert len(repo.list()) == 2


def test_get_missing_returns_none():
    repo = InMemoryFeedbackRepository()
    assert repo.get("does-not-exist") is None


def test_get_existing_feedback_ids():
    repo = InMemoryFeedbackRepository()
    repo.add([FeedbackItem(feedback_id="fb_1", raw_text="a")])
    assert repo.get_existing_feedback_ids() == {"fb_1"}
