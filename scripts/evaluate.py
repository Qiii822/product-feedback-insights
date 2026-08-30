"""评估入口：跑 baseline 评估并打印报告。

用法（在仓库根目录）：
    uv run python -m scripts.evaluate
"""

import json

from app.evaluation.runner import run_all


def main() -> int:
    report = run_all()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
