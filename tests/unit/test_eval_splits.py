"""评估集切分测试：dev / test 互不重叠，test 标签合法。"""

import pytest

from app.evaluation.cases import load_classification_cases
from app.evaluation.runner import run_classification
from app.schemas.enums import IssueType, PrimaryCategory
from tests.fakes import FakeLLM


def _norm(t: str) -> str:
    return " ".join(t.lower().split())


def test_dev_and_test_splits_do_not_overlap():
    dev = {_norm(c["raw_text"]) for c in load_classification_cases("dev")}
    test = {_norm(c["raw_text"]) for c in load_classification_cases("test")}
    assert test
    assert not dev & test


def test_test_split_labels_are_valid():
    cats = {c.value for c in PrimaryCategory}
    types = {t.value for t in IssueType}
    for c in load_classification_cases("test"):
        assert c["expected_category"] in cats, c["id"]
        assert c["expected_issue_type"] in types, c["id"]


def test_unknown_split_rejected():
    with pytest.raises(ValueError):
        load_classification_cases("train")


def test_report_records_split():
    assert run_classification(FakeLLM(), model="fake", split="test")["split"] == "test"
