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

_DIRECTION_ZH = {"rising": "上升", "falling": "下降", "stable": "稳定", "new": "新增"}


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
        t = trend(members, items)
        recent, earlier = t["recent"], t["earlier"]
        growth_norm = round(recent / (recent + earlier), 4) if (recent + earlier) else 0.5
        result[p.id] = {
            "volume": len(members),
            "volume_pct": round(len(members) / total * 100, 1) if total else 0.0,
            "sentiment": sentiment_distribution(members),
            "affected_versions": affected_versions(members),
            "trend": t,
            "growth_norm": growth_norm,  # 近期份额（0~1），供 prioritisation 的增长因子使用
        }
    return result


def compute_facts(problem, metrics: dict) -> list[str]:
    """从确定性指标推导"事实"（FACT），供诊断输出使用。

    只陈述可直接追溯到数据的事实，不含任何推测或根因判断。
    """
    facts = [f"共 {problem.evidence_count} 条反馈，占总反馈 {metrics.get('volume_pct', 0)}%"]

    t = metrics.get("trend", {})
    direction = _DIRECTION_ZH.get(t.get("direction", "stable"), t.get("direction", "stable"))
    facts.append(f"趋势 {direction}：近期 {t.get('recent', 0)} 条 / 早期 {t.get('earlier', 0)} 条")

    s = metrics.get("sentiment", {})
    facts.append(f"情绪：负 {s.get('negative', 0)} · 中 {s.get('neutral', 0)} · 正 {s.get('positive', 0)}")

    if problem.affected_segments:
        facts.append(f"平台：{', '.join(problem.affected_segments)}")
    if metrics.get("affected_versions"):
        facts.append(f"版本：{', '.join(metrics['affected_versions'])}")
    return facts


def compute_executive_summary(items, ranked, metrics) -> dict:
    """从全量反馈与已排序问题，计算 PM 首页所需的执行摘要（确定性）。

    返回：total / negative_rate / positive_rate / sentiment_change / emerging / top_issues。
    """
    total = len(items)
    rated = [i for i in items if i.rating is not None]
    negative = sum(1 for i in rated if i.rating <= 2)
    positive = sum(1 for i in rated if i.rating >= 4)
    negative_rate = round(negative / len(rated) * 100, 1) if rated else 0.0
    positive_rate = round(positive / len(rated) * 100, 1) if rated else 0.0

    # 情绪变化：负评率 近期 vs 早期（按全量时间中位数切分）
    timestamps = sorted(i.timestamp for i in items if i.timestamp is not None)
    if timestamps:
        split = timestamps[len(timestamps) // 2]
        recent_rated = [i for i in rated if i.timestamp is not None and i.timestamp >= split]
        earlier_rated = [i for i in rated if i.timestamp is not None and i.timestamp < split]
        recent_rate = round(sum(1 for i in recent_rated if i.rating <= 2) / len(recent_rated) * 100, 1) if recent_rated else None
        earlier_rate = round(sum(1 for i in earlier_rated if i.rating <= 2) / len(earlier_rated) * 100, 1) if earlier_rated else None
    else:
        recent_rate = earlier_rate = None

    if recent_rate is not None and earlier_rate is not None:
        change = round(recent_rate - earlier_rate, 1)
        direction = "worse" if change >= 5 else ("better" if change <= -5 else "stable")
    else:
        change, direction = 0.0, "stable"

    emerging = []
    for i, p in enumerate(ranked, start=1):
        m = metrics.get(p.id, {})
        t = m.get("trend", {})
        if t.get("direction") in ("new", "rising"):
            emerging.append({
                "id": p.id,
                "title": p.title,
                "rank": i,
                "direction": t.get("direction"),
                "growth_pct": t.get("growth_pct", 0.0),
            })

    top_issues = [
        {
            "id": p.id,
            "title": p.title,
            "rank": i,
            "severity": p.severity.value if p.severity else None,
        }
        for i, p in enumerate(ranked[:3], start=1)
    ]

    return {
        "total": total,
        "negative_rate": negative_rate,
        "positive_rate": positive_rate,
        "rated_count": len(rated),
        "sentiment_change": {
            "recent_rate": recent_rate,
            "earlier_rate": earlier_rate,
            "change": change,
            "direction": direction,
        },
        "emerging": emerging,
        "top_issues": top_issues,
    }
