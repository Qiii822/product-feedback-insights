"""评估集切分：dev / test 互不重叠，test 标签合法，缺失留出集时明确降级。"""

import pytest

from app.evaluation import cases
from app.evaluation.cases import (
    SplitUnavailableError,
    load_classification_cases,
    split_status,
)
from app.evaluation.runner import run_classification
from app.schemas.enums import IssueType, PrimaryCategory
from tests.fakes import FakeLLM

# 留出集需要人工盲标（scripts/build_heldout.py --write）后才存在。
# 标注完成前跳过依赖它的用例，而不是伪造标签让它变绿。
requires_test_split = pytest.mark.skipif(
    not split_status("test")["available"],
    reason="留出集尚未人工盲标（cases_classification_test.json 不存在）",
)


def _norm(t: str) -> str:
    return " ".join(t.lower().split())


@requires_test_split
def test_dev_and_test_splits_do_not_overlap():
    dev = {_norm(c["raw_text"]) for c in load_classification_cases("dev")}
    test = {_norm(c["raw_text"]) for c in load_classification_cases("test")}
    assert test
    assert not dev & test


@requires_test_split
def test_test_split_labels_are_valid():
    cats = {c.value for c in PrimaryCategory}
    types = {t.value for t in IssueType}
    for c in load_classification_cases("test"):
        assert c["expected_category"] in cats, c["id"]
        assert c["expected_issue_type"] in types, c["id"]


def test_unknown_split_rejected():
    with pytest.raises(ValueError):
        load_classification_cases("train")


def test_missing_split_file_raises_split_unavailable_error(monkeypatch):
    monkeypatch.setitem(cases.CLASSIFICATION_SPLITS, "test", "does_not_exist.json")

    with pytest.raises(SplitUnavailableError) as exc:
        load_classification_cases("test")

    # 报错必须能自解释：指出缺哪个文件、怎么补齐
    assert "does_not_exist.json" in str(exc.value)
    assert "build_heldout" in str(exc.value)


def test_split_status_marks_missing_split_unavailable(monkeypatch):
    monkeypatch.setitem(cases.CLASSIFICATION_SPLITS, "test", "does_not_exist.json")

    status = split_status("test")

    assert status["split"] == "test"
    assert status["available"] is False
    assert status["case_count"] == 0
    assert status["pending"]["sheet"].endswith("heldout/review_sheet.csv")


def test_split_status_reports_available_dev_split():
    status = split_status("dev")

    assert status["available"] is True
    assert status["case_count"] == len(load_classification_cases("dev"))
    assert status["pending"] is None


def test_pending_counts_labeled_and_unlabeled_rows(tmp_path, monkeypatch):
    sheet = tmp_path / "review_sheet.csv"
    sheet.write_text(
        "id,raw_text,primary_category,issue_type\n"
        "t001,first,, \n"
        "t002,second,payment_failed,problem\n"
        "t003,third,checkout_stuck,problem\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cases, "HELDOUT_DIR", tmp_path)
    monkeypatch.setitem(cases.CLASSIFICATION_SPLITS, "test", "does_not_exist.json")

    pending = split_status("test")["pending"]

    assert pending["labeled"] == 2
    assert pending["unlabeled"] == 1


def test_report_records_split():
    assert run_classification(FakeLLM(), model="fake", split="dev")["split"] == "dev"
