"""评估数据集加载。

数据集放在 data/eval/ 下，与代码分离、可版本控制。
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "eval"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_classification_cases() -> list[dict]:
    return _load("cases_classification.json")["cases"]


def load_clustering_cases() -> list[dict]:
    return _load("cases_clustering.json")["cases"]


def load_prioritisation_cases() -> dict:
    return _load("cases_prioritisation.json")
