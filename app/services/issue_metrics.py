"""Issue Intelligence 指标（确定性聚合，无 LLM）。

消费反馈的 timestamp / rating / app_version 元数据，为每个 issue 计算：
- volume / volume_pct：反馈量与占比（占总反馈的百分比）
- sentiment_distribution：情绪分布（rating 1-2 负 / 3 中 / 4-5 正 / 无评分未知）
- affected_versions：受影响版本（按频次降序）
- trend：相对全量时间中位数的近期 vs 早期增长信号（上升 / 下降 / 稳定 / 新增）

这些是"数据地基"：全部由确定性规则得出，可解释、可复现，用于回答
"哪些问题在快速恶化 / 影响多大 / 用户多不满"。
"""

from collections import Counter

_SENTIMENT_BUCKETS = ("negative", "neutral", "positive", "unknown")


def _sentiment_of(rating) -> str:
    if rating is None:
        return "unknown"
    if rating <= 2:
        return "negative"
    if rating == 3:
        return "neutral"
    return "positive"  # rating 4~5


def sentiment_distribution(members) -> dict[str, int]:
    """按 rating 把成员反馈分到 negative / neutral / positive / unknown 桶。"""
    dist = {k: 0 for k in _SENTIMENT_BUCKETS}
    for m in members:
        dist[_sentiment_of(m.rating)] += 1
    return dist


def affected_versions(members) -> list[str]:
    """聚合受影响版本（按频次降序）。"""
    versions = [m.app_version for m in members if m.app_version]
    return [v for v, _ in Counter(versions).most_common()]


def trend(members, all_items) -> dict:
    """相对全量时间中位数，比较该 issue 的近期 vs 早期反馈量。

    direction：
    - new：早期为 0、近期有反馈（新兴问题）
    - rising：增长 ≥ +20%
    - falling：下降 ≤ -20%
    - stable：其余
    """
    timestamps = sorted(m.timestamp for m in all_items if m.timestamp is not None)
    if not timestamps:
        return {"recent": 0, "earlier": 0, "growth_pct": 0.0, "direction": "stable"}

    split = timestamps[len(timestamps) // 2]
    recent = sum(1 for m in members if m.timestamp is not None and m.timestamp >= split)
    earlier = sum(1 for m in members if m.timestamp is not None and m.timestamp < split)

    if earlier == 0:
        growth = 100.0 if recent > 0 else 0.0
        direction = "new" if recent > 0 else "stable"
    else:
        growth = round((recent - earlier) / earlier * 100, 1)
        direction = "rising" if growth >= 20 else ("falling" if growth <= -20 else "stable")

    return {"recent": recent, "earlier": earlier, "growth_pct": growth, "direction": direction}


def compute_issue_metrics(items, problems, evidence) -> dict[str, dict]:
    """为每个 problem 计算 Issue Intelligence 指标，返回 {problem_id: metrics}。"""
    item_by_id = {i.id: i for i in items}
    total = len(items)
    result: dict[str, dict] = {}
    for p in problems:
        member_ids = [e.feedback_item_id for e in evidence if e.product_problem_id == p.id]
        members = [item_by_id[mid] for mid in member_ids if mid in item_by_id]
        result[p.id] = {
            "volume": len(members),
            "volume_pct": round(len(members) / total * 100, 1) if total else 0.0,
            "sentiment": sentiment_distribution(members),
            "affected_versions": affected_versions(members),
            "trend": trend(members, items),
        }
    return result
