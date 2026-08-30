"""优先级排序测试。"""

from app.schemas.enums import PrimaryCategory, ProblemStatus, Severity
from app.schemas.problem import ProductProblem
from app.services.prioritisation import WeightedPrioritisationService


def _problem(evidence_count, severity, segments=None, needs_review=False):
    return ProductProblem(
        title="x",
        category=PrimaryCategory.PAYMENT_FAILED,
        severity=severity,
        affected_segments=segments or [],
        evidence_count=evidence_count,
        needs_review=needs_review,
    )


def test_higher_severity_and_frequency_scores_higher():
    svc = WeightedPrioritisationService()
    low = _problem(2, Severity.LOW)
    high = _problem(5, Severity.CRITICAL)
    assert svc.score(high) > svc.score(low)


def test_removed_impact_double_counting():
    # V2：critical + 8 条 应排在 high + 15 条 之上（不再被 impact 项虚高）
    svc = WeightedPrioritisationService()
    critical_few = _problem(8, Severity.CRITICAL)
    high_many = _problem(15, Severity.HIGH)
    assert svc.score(critical_few) > svc.score(high_many)


def test_prioritize_ranks_confirmed_descending_and_excludes_candidates():
    svc = WeightedPrioritisationService()
    a = _problem(3, Severity.HIGH)
    b = _problem(5, Severity.CRITICAL)
    c = _problem(1, Severity.LOW, needs_review=True)  # candidate，不参与 ranking
    ranked = svc.prioritize([a, b, c])
    assert len(ranked) == 2  # 只排 confirmed
    assert ranked[0].priority_score >= ranked[1].priority_score
    assert ranked[0].status is ProblemStatus.PRIORITIZED
