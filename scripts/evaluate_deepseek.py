"""用真实 DeepSeek 跑分类评估。

用法（在仓库根目录，需先设置 DEEPSEEK_API_KEY）：
    uv run python -m scripts.evaluate_deepseek
"""

import json
import sys

from app.core.config import settings
from app.evaluation.runner import run_classification
from app.services.llm import DeepSeekProvider


def main() -> int:
    if not settings.deepseek_api_key:
        print("未设置 DEEPSEEK_API_KEY（请在 .env 或环境变量中提供）", file=sys.stderr)
        return 1
    llm = DeepSeekProvider(settings.deepseek_api_key, model=settings.deepseek_model)
    report = run_classification(llm, model=settings.deepseek_model)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
