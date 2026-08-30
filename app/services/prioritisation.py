"""优先级排序（prioritisation）：问题列表 → 按优先级排序。

决策（Phase 5 V2）：确定性加权打分，透明可解释，权重可配置。

score = w_severity·severity_norm + w_frequency·frequency_norm + w_breadth·breadth_norm

- severity_norm = 严重程度序数 / 4（low=1 … critical=4）
- frequency_norm = min(证据数, 10) / 10
- breadth_norm = min(受影响平台数, 3) / 3

V2 移除了 impact = severity × frequency 项：它与 severity / frequency 项重复计算，
会让高频问题虚高（evaluation 证实导致 ranking 与 PM 判断不一致）。

只对 confirmed（needs_review=False）问题打分排序；candidate 不进入 ranking。
"""

from app.schemas.enums import ProblemStatus, Severity
from app.schemas.problem import ProductProblem
from app.services.interfaces import PrioritisationService

_SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

_DEFAULT_WEIGHTS = {
    "severity": 1.0,
    "frequency": 1.0,
    "breadth": 0.5,
}


class WeightedPrioritisationService(PrioritisationService):
    """确定性加权优先级排序。"""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or _DEFAULT_WEIGHTS

    def score(self, problem: ProductProblem) -> float:
        severity = _SEVERITY_RANK.get(problem.severity, 0)
        frequency = problem.evidence_count
        breadth = len(problem.affected_segments)

        severity_norm = severity / 4.0
        frequency_norm = min(frequency, 10) / 10.0
        breadth_norm = min(breadth, 3) / 3.0

        return (
            self._weights["severity"] * severity_norm
            + self._weights["frequency"] * frequency_norm
            + self._weights["breadth"] * breadth_norm
        )

    def prioritize(self, problems: list[ProductProblem]) -> list[ProductProblem]:
        """只对 confirmed 问题打分并降序排序；candidate 不进入 ranking。"""
        confirmed = [p for p in problems if not p.needs_review]
        for p in confirmed:
            p.priority_score = round(self.score(p), 4)
            p.status = ProblemStatus.PRIORITIZED
        return sorted(confirmed, key=lambda p: p.priority_score, reverse=True)
