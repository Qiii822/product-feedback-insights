"""把人工盲标的审核表与生成意图合并，产出留出测试集。

用法：
    uv run python -m scripts.build_heldout            # 列出人工标签与生成意图不一致的条目
    uv run python -m scripts.build_heldout --write    # 全部裁决后写出 cases_classification_test.json

最终标签以人工标注（review_sheet.csv）为准；生成意图只用于发现分歧。
"""

import argparse
import csv
import json
from datetime import date

from app.evaluation.cases import DATA_DIR
from app.schemas.enums import IssueType, PrimaryCategory

HELDOUT = DATA_DIR / "heldout"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    intents = {c["id"]: c for c in json.load(open(HELDOUT / "intent_hidden.json"))["cases"]}
    with open(HELDOUT / "review_sheet.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    cats = {c.value for c in PrimaryCategory}
    types = {t.value for t in IssueType}
    invalid = [
        r["id"]
        for r in rows
        if r["primary_category"].strip() not in cats or r["issue_type"].strip() not in types
    ]
    if invalid:
        print(f"未标注或标签非法：{invalid}")
        return 1

    disagree = [r for r in rows if r["primary_category"].strip() != intents[r["id"]]["intent_category"]]
    for r in disagree:
        print(f'{r["id"]}  人工={r["primary_category"]}  意图={intents[r["id"]]["intent_category"]}  | {r["raw_text"]}')
    print(f"\n类别分歧 {len(disagree)}/{len(rows)}（{len(disagree) / len(rows):.0%}）")

    if args.write:
        out = {
            "version": "v1",
            "dimension": "classification",
            "split": "test",
            "frozen_on": date.today().isoformat(),
            "note": "留出测试集：文本由非被测模型（Claude）合成，标签由人工盲标（不可见生成意图）。"
            "只用于报告泛化指标，禁止据其失败样例修改 prompt。",
            "label_intent_disagreement_rate": round(len(disagree) / len(rows), 4),
            "cases": [
                {
                    "id": r["id"],
                    "raw_text": r["raw_text"],
                    "expected_category": r["primary_category"].strip(),
                    "expected_issue_type": r["issue_type"].strip(),
                }
                for r in rows
            ],
        }
        with open(DATA_DIR / "cases_classification_test.json", "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print("已写出 cases_classification_test.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
