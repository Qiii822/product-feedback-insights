"""摄取（ingestion）模块。

流程：文件（CSV/JSON）→ 解析 → 归一化（含校验）→ 精确去重 → 持久化。

去重决策（Phase 2）：仅做"精确去重"——以 feedback_id 为身份标识，
同一 feedback_id 再次出现即视为重复（含重复导入 / 同批内重复）。
语义相似的判断留到 clustering 阶段，不在摄取层处理。
"""

import csv
import json
from pathlib import Path

from app.schemas.ingestion import IngestionResult
from app.services.interfaces import FeedbackRepository
from app.services.normalization import normalize_row

REQUIRED_COLUMNS = {"feedback_id", "raw_text"}


def parse_csv(path) -> list[dict]:
    """读取 CSV 为行字典列表；校验必填列存在。"""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV 无表头")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV 缺少必填列：{sorted(missing)}")
        return list(reader)


def parse_json(path) -> list[dict]:
    """读取 JSON（顶层为数组）为行字典列表。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON 顶层必须是数组")
    return data


def parse_file(path) -> list[dict]:
    """按扩展名分发解析。"""
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return parse_csv(path)
    if suffix == ".json":
        return parse_json(path)
    raise ValueError(f"不支持的文件类型：{suffix}（仅支持 .csv / .json）")


class IngestionService:
    """摄取编排：归一化 → 精确去重 → 持久化。"""

    def __init__(self, repository: FeedbackRepository):
        self._repository = repository

    def ingest(self, rows: list[dict]) -> IngestionResult:
        """摄取一批原始行，返回统计结果。"""
        existing = self._repository.get_existing_feedback_ids()
        seen = set(existing)
        to_add = []
        invalid_reasons: list[str] = []
        warnings: list[str] = []
        skipped = 0

        for i, row in enumerate(rows, start=1):
            try:
                normalized = normalize_row(row)
            except ValueError as exc:
                invalid_reasons.append(f"row {i}: {exc}")
                continue
            if normalized.item.feedback_id in seen:
                skipped += 1
                continue
            seen.add(normalized.item.feedback_id)
            to_add.append(normalized.item)
            for w in normalized.warnings:
                warnings.append(f"row {i}: {w}")

        self._repository.add(to_add)

        return IngestionResult(
            total_rows=len(rows),
            added=len(to_add),
            skipped_duplicates=skipped,
            invalid=len(invalid_reasons),
            errors=invalid_reasons,
            warnings=warnings,
        )

    def ingest_file(self, path) -> IngestionResult:
        """从文件路径摄取（按扩展名分发）。"""
        return self.ingest(parse_file(path))
