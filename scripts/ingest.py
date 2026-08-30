"""摄取命令行入口。

用法（在仓库根目录）：
    uv run python -m scripts.ingest data/raw/sample_feedback.csv

这是一个薄薄的演示入口：把文件摄取流程串起来并打印统计结果。
"""

import sys

from app.db.session import SessionLocal
from app.repositories.sql import SQLFeedbackRepository
from app.services.ingestion import IngestionService


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("用法: python -m scripts.ingest <path-to-csv-or-json>", file=sys.stderr)
        return 2

    path = argv[1]
    service = IngestionService(SQLFeedbackRepository(SessionLocal))
    try:
        result = service.ingest_file(path)
    except (ValueError, OSError) as exc:
        print(f"摄取失败：{exc}", file=sys.stderr)
        return 1

    print(f"总行数: {result.total_rows}")
    print(f"新增: {result.added}")
    print(f"跳过重复: {result.skipped_duplicates}")
    print(f"无效: {result.invalid}")
    for err in result.errors:
        print(f"  - [错误] {err}")
    for w in result.warnings:
        print(f"  - [警告] {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
