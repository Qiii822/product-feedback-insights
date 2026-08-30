"""归一化（normalization）纯函数模块。

Phase 2 的 "validation + normalization"：把原始 CSV/JSON 行转成
规范化后的 FeedbackItem。规则集中在这里，便于测试与评审。

关键决策：
- 枚举字段（source / platform / customer_segment）：
  - 未提供（None / 空串）→ None
  - 提供了但无法映射 → "unknown"（D8.3：区分"缺失"与"无法识别"）
- 映射表是普通 dict，保持未来扩展（新增别名只需加一行）。
- rating：缺失 → None（无警告）；提供了但解析失败/越界 → None + 警告，
  但不丢弃整条反馈（D8.2）。
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.schemas.feedback import FeedbackItem

# —— 枚举标准化映射（可扩展）——
SOURCE_MAP: dict[str, str] = {
    "app_review": "app_review", "review": "app_review", "appstore": "app_review",
    "support_ticket": "support_ticket", "ticket": "support_ticket",
    "nps": "nps",
    "survey": "survey",
    "in_app": "in_app",
}

PLATFORM_MAP: dict[str, str] = {
    "ios": "ios", "iphone": "ios", "ipad": "ios", "apple": "ios",
    "android": "android",
    "web": "web", "browser": "web", "desktop": "web",
}

SEGMENT_MAP: dict[str, str] = {
    "free": "free", "paid": "paid", "premium": "premium",
    "trial": "trial", "enterprise": "enterprise",
}

_WHITESPACE_RE = re.compile(r"\s+")


def _as_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_raw_text(text) -> str:
    """去除首尾空白，并把连续空白折叠为单个空格。"""
    return _WHITESPACE_RE.sub(" ", _as_str(text)).strip()


def normalize_enum(value, mapping: dict[str, str]) -> str | None:
    """把字段标准化为小写规范值。

    - 未提供（None / 空串）→ None
    - 提供了但无法映射 → "unknown"
    """
    s = _as_str(value)
    if not s:
        return None
    key = s.lower()
    return mapping.get(key, "unknown")


def normalize_optional(value) -> str | None:
    """自由文本字段（如 app_version）：空 → None，否则去空白返回。"""
    s = _as_str(value)
    return s or None


def normalize_rating(value) -> int | None:
    """解析 1~5 的整数评分；缺失或解析失败/越界 → None。"""
    s = _as_str(value)
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    if not f.is_integer():
        return None
    r = int(f)
    return r if 1 <= r <= 5 else None


def parse_timestamp(value) -> datetime | None:
    """解析 ISO-8601 时间戳；解析失败 → None。"""
    s = _as_str(value)
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class NormalizedRow:
    """归一化结果：规范化的 FeedbackItem + 非致命警告。"""

    item: FeedbackItem
    warnings: list[str] = field(default_factory=list)


def normalize_row(row: dict) -> NormalizedRow:
    """把一行原始数据转成规范化的 NormalizedRow。

    结构校验：feedback_id 与 raw_text 必填且非空，否则抛 ValueError（致命）。
    非致命问题（如 rating 无效）记录到 warnings，不抛异常、不丢弃该行。
    """
    feedback_id = _as_str(row.get("feedback_id"))
    raw_text = _as_str(row.get("raw_text"))
    if not feedback_id:
        raise ValueError("feedback_id 缺失或为空")
    if not raw_text:
        raise ValueError("raw_text 缺失或为空")

    warnings: list[str] = []
    rating_raw = row.get("rating")
    rating = normalize_rating(rating_raw)
    # D8.2：rating 提供了但无效 → 置 None 并记录警告（不丢弃整条反馈）
    if rating is None and _as_str(rating_raw):
        warnings.append(f"rating 无效（值 '{_as_str(rating_raw)}'），已置为 None")

    return NormalizedRow(
        item=FeedbackItem(
            feedback_id=feedback_id,
            raw_text=normalize_raw_text(raw_text),
            source=normalize_enum(row.get("source"), SOURCE_MAP),
            platform=normalize_enum(row.get("platform"), PLATFORM_MAP),
            app_version=normalize_optional(row.get("app_version")),
            customer_segment=normalize_enum(row.get("customer_segment"), SEGMENT_MAP),
            rating=rating,
            timestamp=parse_timestamp(row.get("timestamp")),
        ),
        warnings=warnings,
    )
