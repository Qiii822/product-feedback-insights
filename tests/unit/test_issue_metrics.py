"""Issue Intelligence 指标（确定性聚合）测试。"""

from datetime import datetime, timezone

from app.schemas.evidence import Evidence
from app.schemas.feedback import FeedbackItem
from app.schemas.problem import ProductProblem
from app.services.issue_metrics import (
    affected_versions,
    compute_issue_metrics,
    sentiment_distribution,
    trend,
)


def _ts(day: int) -> datetime:
    return datetime(2026, 8, day, tzinfo=timezone.utc)


def _item(iid, rating=None, version=None, day=1):
    return FeedbackItem(
        id=iid,
        feedback_id=iid,
        raw_text="x",
        rating=rating,
        app_version=version,
        timestamp=_ts(day),
    )


def test_sentiment_distribution_buckets_by_rating():
    items = [
        _item("a", rating=1),
        _item("b", rating=2),
        _item("c", rating=3),
        _item("d", rating=4),
        _item("e", rating=5),
        _item("f", rating=None),
    ]
    assert sentiment_distribution(items) == {
        "negative": 2, "neutral": 1, "positive": 2, "unknown": 1,
    }


def test_affected_versions_sorted_by_frequency():
    items = [
        _item("a", version="2.1.0"),
        _item("b", version="2.1.1"),
        _item("c", version="2.1.0"),
        _item("d", version=None),
    ]
    assert affected_versions(items) == ["2.1.0", "2.1.1"]


def test_trend_new_when_only_recent():
    all_items = [_item(f"t{i}", day=1 + i) for i in range(10)]  # day 1..10
    members = [_item(f"m{i}", day=9 + i) for i in range(2)]      # day 9,10（都在近期）
    assert trend(members, all_items)["direction"] == "new"


def test_trend_rising_when_recent_heavier():
    all_items = [_item(f"t{i}", day=1 + i) for i in range(10)]  # day 1..10，中位数 ~day6
    members = [_item("a", day=1), _item("b", day=8), _item("c", day=9), _item("d", day=10)]
    t = trend(members, all_items)
    assert t["recent"] == 3
    assert t["earlier"] == 1
    assert t["direction"] == "rising"


def test_compute_issue_metrics_volume_pct_sentiment_versions():
    items = [
        _item("a", rating=1, version="2.1.0", day=1),
        _item("b", rating=2, version="2.1.0", day=2),
        _item("c", rating=5, version="2.1.1", day=3),
        _item("d", rating=4, version="2.1.1", day=4),
    ]
    problem = ProductProblem(id="p1", title="支付失败")
    evidence = [
        Evidence(product_problem_id="p1", feedback_item_id="a"),
        Evidence(product_problem_id="p1", feedback_item_id="b"),
    ]
    m = compute_issue_metrics(items, [problem], evidence)["p1"]
    assert m["volume"] == 2
    assert m["volume_pct"] == 50.0
    assert m["sentiment"]["negative"] == 2
    assert m["affected_versions"] == ["2.1.0"]
