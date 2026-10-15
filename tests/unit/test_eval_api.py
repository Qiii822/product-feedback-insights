"""POST /api/evaluate 的 split 契约。

留出集（cases_classification_test.json）在人工盲标完成前不存在。此时端点必须
返回「待标注」占位（200 + available=false），而不是报错，并且**不得触碰 LLM**
——否则未配置 DEEPSEEK_API_KEY 时连"留出集还没标"这件事都看不到。

测试用 monkeypatch 把 test split 指向一个不存在的文件，因此这些用例断言的是
分支行为，而不是仓库当前恰好缺文件的状态：标注完成后它们依然成立。
"""

from app.api.routes import pipeline as pipeline_routes
from app.evaluation import cases
from tests.fakes import FakeLLM


def test_unlabeled_test_split_returns_pending_placeholder(client, monkeypatch):
    monkeypatch.setitem(cases.CLASSIFICATION_SPLITS, "test", "does_not_exist.json")

    resp = client.post("/api/evaluate?split=test")

    assert resp.status_code == 200
    body = resp.json()
    assert body["split"] == "test"
    assert body["available"] is False
    assert body["pending"]["build_command"] == "uv run python -m scripts.build_heldout --write"
    # 未标注就不该产出任何指标——否则空集上的 0.0 会被误读成"成绩很差"
    assert "accuracy" not in body
    assert "per_category" not in body


def test_unlabeled_test_split_does_not_initialize_llm(client, monkeypatch):
    monkeypatch.setitem(cases.CLASSIFICATION_SPLITS, "test", "does_not_exist.json")

    def _boom():
        raise AssertionError("未标注分支不得初始化 LLM")

    monkeypatch.setattr(pipeline_routes, "get_llm", _boom)

    assert client.post("/api/evaluate?split=test").status_code == 200


def test_unknown_split_is_rejected(client):
    assert client.post("/api/evaluate?split=train").status_code == 422


def test_evaluate_defaults_to_dev_split(client, monkeypatch):
    monkeypatch.setattr(pipeline_routes, "get_llm", lambda: FakeLLM())

    body = client.post("/api/evaluate").json()

    assert body["split"] == "dev"
    assert body["available"] is True


def test_dev_split_returns_full_report(client, monkeypatch):
    monkeypatch.setattr(pipeline_routes, "get_llm", lambda: FakeLLM())

    body = client.post("/api/evaluate?split=dev").json()

    assert body["available"] is True
    assert body["n"] == len(cases.load_classification_cases("dev"))
    assert {"accuracy", "macro_f1", "per_category", "calibration"} <= set(body)
