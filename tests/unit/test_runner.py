"""评估 runner 测试：锁定 UI 依赖的评估报告字段契约。"""

from app.evaluation.runner import run_classification
from tests.fakes import FakeLLM


def test_classification_report_contains_ui_fields():
    report = run_classification(FakeLLM(), model="fake")
    # UI 渲染依赖这些字段，缺失会导致前端崩坏
    for key in (
        "n",
        "model",
        "accuracy",
        "macro_f1",
        "issue_type_accuracy",
        "needs_review_rate",
        "needs_review_recall",
        "per_category",
        "calibration",
    ):
        assert key in report
    assert "ece" in report["calibration"]
    assert isinstance(report["calibration"]["reliability"], list)
    assert len(report["per_category"]) >= 1
