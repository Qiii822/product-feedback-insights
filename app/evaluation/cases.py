"""评估数据集加载。

数据集放在 data/eval/ 下，与代码分离、可版本控制。
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "eval"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


CLASSIFICATION_SPLITS = {
    # dev：用于 prompt 迭代，指标是"调参成绩"
    "dev": "cases_classification.json",
    # test：留出集，只用于报告泛化指标，禁止据其失败样例改 prompt（见 ADR）
    "test": "cases_classification_test.json",
}


def load_classification_cases(split: str = "dev") -> list[dict]:
    if split not in CLASSIFICATION_SPLITS:
        raise ValueError(f"unknown split: {split!r}（可选：{sorted(CLASSIFICATION_SPLITS)}）")
    return _load(CLASSIFICATION_SPLITS[split])["cases"]


def load_clustering_cases() -> list[dict]:
    return _load("cases_clustering.json")["cases"]


def load_prioritisation_cases() -> dict:
    return _load("cases_prioritisation.json")
