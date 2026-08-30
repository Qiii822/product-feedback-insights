"""Pydantic 数据契约测试。

验证：必填字段、默认值、以及"非法数据必须被拒绝"（置信度越界等）。
"""

import pytest
from pydantic import ValidationError

from app.schemas.analysis import FeedbackAnalysis
from app.schemas.enums import Severity
from app.schemas.feedback import FeedbackItem


def test_feedback_item_requires_raw_text():
    with pytest.raises(ValidationError):
        FeedbackItem(feedback_id="fb_1")  # 缺 raw_text


def test_feedback_item_requires_feedback_id():
    with pytest.raises(ValidationError):
        FeedbackItem(raw_text="Payment failed again.")  # 缺 feedback_id


def test_feedback_item_defaults():
    item = FeedbackItem(feedback_id="fb_1", raw_text="Payment failed again.")
    assert item.source is None
    assert item.platform is None
    assert item.customer_segment is None
    assert item.app_version is None
    assert item.rating is None
    assert item.timestamp is None


def test_feedback_item_fixed_fields():
    item = FeedbackItem(
        feedback_id="fb_1", raw_text="x", platform="ios", rating=4, app_version="2.1.0"
    )
    assert item.platform == "ios"
    assert item.rating == 4
    assert item.app_version == "2.1.0"


def test_feedback_item_rating_bounds():
    with pytest.raises(ValidationError):
        FeedbackItem(feedback_id="fb_1", raw_text="x", rating=6)
    with pytest.raises(ValidationError):
        FeedbackItem(feedback_id="fb_1", raw_text="x", rating=0)


def test_analysis_severity_coerces_from_string():
    a = FeedbackAnalysis(
        summary="支付失败",
        primary_category="payment_failed",
        issue_type="problem",
        severity="high",
        confidence=0.9,
    )
    assert a.severity is Severity.HIGH


def test_analysis_requires_issue_type():
    with pytest.raises(ValidationError):
        FeedbackAnalysis(
            summary="x", primary_category="payment_failed", severity="high", confidence=0.9
        )


def test_analysis_rejects_invalid_category():
    with pytest.raises(ValidationError):
        FeedbackAnalysis(
            summary="x", primary_category="not_a_category", issue_type="problem",
            severity="high", confidence=0.9,
        )


def test_analysis_confidence_rejects_out_of_bounds():
    base = dict(primary_category="payment_failed", issue_type="problem", severity="high")
    with pytest.raises(ValidationError):
        FeedbackAnalysis(summary="x", confidence=1.5, **base)
    with pytest.raises(ValidationError):
        FeedbackAnalysis(summary="x", confidence=-0.1, **base)


def test_analysis_confidence_accepts_boundary():
    a = FeedbackAnalysis(
        summary="x",
        primary_category="payment_failed",
        issue_type="problem",
        severity="low",
        confidence=1.0,
    )
    assert a.confidence == 1.0


def test_analysis_needs_review_defaults_false():
    a = FeedbackAnalysis(
        summary="x",
        primary_category="other",
        issue_type="question",
        severity="low",
        confidence=0.5,
    )
    assert a.needs_review is False
