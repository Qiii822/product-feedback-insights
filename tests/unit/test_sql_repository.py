"""SQLFeedbackRepository 测试（真实 SQLite 内存库，验证持久化）。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.repositories.sql import SQLFeedbackRepository
from app.schemas.feedback import FeedbackItem


def _make_repo() -> SQLFeedbackRepository:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return SQLFeedbackRepository(sessionmaker(bind=engine))


def test_add_and_get_roundtrip():
    repo = _make_repo()
    item = FeedbackItem(feedback_id="fb_1", raw_text="Payment failed", platform="ios")
    repo.add([item])
    got = repo.get(item.id)
    assert got is not None
    assert got.feedback_id == "fb_1"
    assert got.raw_text == "Payment failed"
    assert got.platform == "ios"


def test_get_missing_returns_none():
    repo = _make_repo()
    assert repo.get("nope") is None


def test_list_and_feedback_ids():
    repo = _make_repo()
    repo.add(
        [
            FeedbackItem(feedback_id="fb_1", raw_text="a"),
            FeedbackItem(feedback_id="fb_2", raw_text="b"),
        ]
    )
    assert len(repo.list()) == 2
    assert repo.get_existing_feedback_ids() == {"fb_1", "fb_2"}
