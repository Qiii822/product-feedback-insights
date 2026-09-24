"""评估入口：跑完整评估（分类 / 聚类 / 排序）并打印报告。

用法（在仓库根目录，需先设置 DEEPSEEK_API_KEY）：
    uv run python -m scripts.evaluate
"""

import json

from app.core.config import settings
from app.evaluation.runner import run_all
from app.services.llm import get_llm


def main() -> int:
    report = run_all(get_llm(), model=settings.deepseek_model)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
