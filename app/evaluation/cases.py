"""评估数据集加载。

数据集放在 data/eval/ 下，与代码分离、可版本控制。

留出集（test）需要人工盲标后才存在。缺失时抛 `SplitUnavailableError` 而不是
裸 FileNotFoundError——调用方（API / UI）据此把该 split 明确降级为「待标注」，
而不是把它当成故障。
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "eval"
HELDOUT_DIR = DATA_DIR / "heldout"

BUILD_HELDOUT_COMMAND = "uv run python -m scripts.build_heldout --write"

CLASSIFICATION_SPLITS = {
    # dev：用于 prompt 迭代，指标是"调参成绩"
    "dev": "cases_classification.json",
    # test：留出集，只用于报告泛化指标，禁止据其失败样例改 prompt（见 ADR）
    "test": "cases_classification_test.json",
}


class SplitUnavailableError(ValueError):
    """split 尚无数据（典型情况：留出集还没人工盲标）。"""


def _load(name: str) -> dict:
    path = DATA_DIR / name
    if not path.exists():
        raise SplitUnavailableError(
            f"评估集 {name} 不存在（{path}）。"
            f"先人工盲标 {HELDOUT_DIR / 'review_sheet.csv'}，"
            f"再运行 `{BUILD_HELDOUT_COMMAND}` 写出测试集。"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pending_labels() -> dict:
    """留出集人工盲标进度：review_sheet.csv 中标签仍为空的行数。"""
    sheet = HELDOUT_DIR / "review_sheet.csv"
    if not sheet.exists():
        return {
            "sheet": str(sheet),
            "labeled": 0,
            "unlabeled": 0,
            "build_command": BUILD_HELDOUT_COMMAND,
        }
    with open(sheet, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    unlabeled = sum(
        1
        for r in rows
        if not (r.get("primary_category") or "").strip()
        or not (r.get("issue_type") or "").strip()
    )
    return {
        "sheet": str(sheet),
        "labeled": len(rows) - unlabeled,
        "unlabeled": unlabeled,
        "build_command": BUILD_HELDOUT_COMMAND,
    }


def split_status(split: str) -> dict:
    """报告某 split 的可用状态（供 API / UI 在缺失时明确降级）。"""
    if split not in CLASSIFICATION_SPLITS:
        raise ValueError(f"unknown split: {split!r}（可选：{sorted(CLASSIFICATION_SPLITS)}）")
    name = CLASSIFICATION_SPLITS[split]
    available = (DATA_DIR / name).exists()
    return {
        "split": split,
        "available": available,
        "case_count": len(_load(name)["cases"]) if available else 0,
        "source": name,
        "pending": None if available else _pending_labels(),
    }


def load_classification_cases(split: str = "dev") -> list[dict]:
    if split not in CLASSIFICATION_SPLITS:
        raise ValueError(f"unknown split: {split!r}（可选：{sorted(CLASSIFICATION_SPLITS)}）")
    return _load(CLASSIFICATION_SPLITS[split])["cases"]


def load_clustering_cases() -> list[dict]:
    return _load("cases_clustering.json")["cases"]


def load_prioritisation_cases() -> dict:
    return _load("cases_prioritisation.json")
