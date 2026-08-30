"""摄取（ingestion）流程测试。"""

import pytest

from app.repositories.memory import InMemoryFeedbackRepository
from app.schemas.feedback import FeedbackItem
from app.services.ingestion import IngestionService, parse_csv, parse_json


def test_parse_csv_reads_rows(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("feedback_id,raw_text\nfb_1,Payment failed\nfb_2,Checkout stuck\n", encoding="utf-8")
    rows = parse_csv(p)
    assert rows == [
        {"feedback_id": "fb_1", "raw_text": "Payment failed"},
        {"feedback_id": "fb_2", "raw_text": "Checkout stuck"},
    ]


def test_parse_csv_requires_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("feedback_id,text\n1,hello\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_csv(p)


def test_parse_json_list(tmp_path):
    p = tmp_path / "f.json"
    p.write_text('[{"feedback_id":"fb_1","raw_text":"x"}]', encoding="utf-8")
    assert parse_json(p) == [{"feedback_id": "fb_1", "raw_text": "x"}]


def test_parse_json_rejects_non_list(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"feedback_id":"fb_1"}', encoding="utf-8")
    with pytest.raises(ValueError):
        parse_json(p)


def test_ingest_adds_and_skips_duplicates():
    repo = InMemoryFeedbackRepository()
    svc = IngestionService(repo)
    rows = [
        {"feedback_id": "fb_1", "raw_text": "Payment failed"},
        {"feedback_id": "fb_1", "raw_text": "Payment failed"},  # 同批重复
        {"feedback_id": "fb_2", "raw_text": "Checkout stuck"},
        {"raw_text": "missing id"},  # 无效行
    ]
    result = svc.ingest(rows)
    assert result.total_rows == 4
    assert result.added == 2
    assert result.skipped_duplicates == 1
    assert result.invalid == 1
    assert len(repo.list()) == 2


def test_ingest_dedups_against_existing():
    repo = InMemoryFeedbackRepository()
    repo.add([FeedbackItem(feedback_id="fb_1", raw_text="Payment failed")])
    svc = IngestionService(repo)
    result = svc.ingest([{"feedback_id": "fb_1", "raw_text": "Payment failed"}])
    assert result.added == 0
    assert result.skipped_duplicates == 1


def test_ingest_warns_on_invalid_rating_but_keeps_row():
    repo = InMemoryFeedbackRepository()
    svc = IngestionService(repo)
    result = svc.ingest([{"feedback_id": "fb_1", "raw_text": "Payment failed", "rating": "abc"}])
    assert result.added == 1
    assert result.invalid == 0
    assert len(result.warnings) == 1
    assert repo.list()[0].rating is None
