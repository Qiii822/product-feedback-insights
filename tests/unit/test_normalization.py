"""归一化（normalization）规则测试。"""

import pytest

from app.schemas.feedback import FeedbackItem
from app.services.normalization import (
    PLATFORM_MAP,
    normalize_enum,
    normalize_rating,
    normalize_raw_text,
    normalize_row,
    parse_timestamp,
)


def test_normalize_raw_text_collapses_whitespace():
    assert normalize_raw_text("  Payment   failed\n again. ") == "Payment failed again."


def test_normalize_enum_maps_alias():
    assert normalize_enum("iPhone", PLATFORM_MAP) == "ios"
    assert normalize_enum("  iOS ", PLATFORM_MAP) == "ios"
    assert normalize_enum("android", PLATFORM_MAP) == "android"


def test_normalize_enum_missing_is_none():
    assert normalize_enum(None, PLATFORM_MAP) is None
    assert normalize_enum("", PLATFORM_MAP) is None
    assert normalize_enum("   ", PLATFORM_MAP) is None


def test_normalize_enum_unmapped_is_unknown():
    assert normalize_enum("blackberry", PLATFORM_MAP) == "unknown"


def test_normalize_rating():
    assert normalize_rating("5") == 5
    assert normalize_rating("5.0") == 5
    assert normalize_rating("4.5") is None
    assert normalize_rating("abc") is None
    assert normalize_rating("7") is None
    assert normalize_rating("") is None
    assert normalize_rating(None) is None


def test_parse_timestamp():
    ts = parse_timestamp("2026-08-01T09:00:00Z")
    assert ts is not None
    assert ts.year == 2026 and ts.month == 8 and ts.day == 1
    assert parse_timestamp("not-a-date") is None
    assert parse_timestamp(None) is None


def test_normalize_row_full():
    normalized = normalize_row(
        {
            "feedback_id": " fb_001 ",
            "raw_text": "  Payment   failed again. ",
            "source": "Review",
            "platform": "iPhone",
            "app_version": " 2.1.0 ",
            "customer_segment": "Paid",
            "rating": "5",
            "timestamp": "2026-08-01T09:00:00Z",
        }
    )
    item = normalized.item
    assert isinstance(item, FeedbackItem)
    assert item.feedback_id == "fb_001"
    assert item.raw_text == "Payment failed again."
    assert item.source == "app_review"
    assert item.platform == "ios"
    assert item.app_version == "2.1.0"
    assert item.customer_segment == "paid"
    assert item.rating == 5
    assert item.timestamp is not None
    assert normalized.warnings == []


def test_normalize_row_missing_vs_unknown():
    # D8.3：未提供 → None；提供了但无法映射 → "unknown"
    normalized = normalize_row(
        {
            "feedback_id": "fb_1",
            "raw_text": "x",
            "source": "reddit",  # 无法映射 → "unknown"
            "platform": "",  # 未提供 → None
            "customer_segment": None,  # 未提供 → None
        }
    )
    assert normalized.item.source == "unknown"
    assert normalized.item.platform is None
    assert normalized.item.customer_segment is None


def test_normalize_row_invalid_rating_warns_but_keeps():
    # D8.2：rating 无效 → None + 警告，但不丢弃该行
    normalized = normalize_row({"feedback_id": "fb_1", "raw_text": "x", "rating": "abc"})
    assert normalized.item.rating is None
    assert len(normalized.warnings) == 1
    assert "rating" in normalized.warnings[0]


def test_normalize_row_missing_rating_no_warning():
    normalized = normalize_row({"feedback_id": "fb_1", "raw_text": "x"})
    assert normalized.item.rating is None
    assert normalized.warnings == []


@pytest.mark.parametrize("missing", ["feedback_id", "raw_text"])
def test_normalize_row_requires_fields(missing):
    row = {"feedback_id": "fb_001", "raw_text": "Payment failed."}
    row[missing] = ""
    with pytest.raises(ValueError):
        normalize_row(row)
