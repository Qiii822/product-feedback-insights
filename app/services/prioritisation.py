"""优先级排序（prioritisation）：问题列表 → 按优先级排序。

决策（Phase 5 V3）：确定性加权打分，透明、可解释、可分解。

score = Σ weightᵢ · normalizedᵢ，因子：
- severity 严重度（序数 / 4）
- volume   量（min(证据数, 10) / 10）
- growth   增长（近期份额 recent/(recent+earlier)，来自 Issue Intelligence 的 trend）
- breadth  广度（min(受影响平台数, 3) / 3）

factor_breakdown() 返回每个因子的 name / weight / normalized / contribution，
让 PM 能回答"为什么排在这里"。growth 缺省 0.5（无时间数据时中性）。

只对 confirmed（needs_review=False）打分排序；candidate 不进入 ranking。
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
    "volume": 1.0,
    "growth": 1.0,
    "breadth": 0.5,
}


def _severity_norm(severity) -> float:
    return _SEVERITY_RANK.get(severity, 0) / 4.0


def _volume_norm(evidence_count: int) -> float:
    return min(evidence_count, 10) / 10.0


def _breadth_norm(affected_segments: list) -> float:
    return min(len(affected_segments), 3) / 3.0


def _growth_norm(growth: float) -> float:
    return max(0.0, min(1.0, growth))


class WeightedPrioritisationService(PrioritisationService):
    """确定性加权优先级排序（V3：含 growth 因子，可分解、可解释）。"""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or _DEFAULT_WEIGHTS

    def factor_breakdown(self, problem: ProductProblem, growth: float = 0.5) -> list[dict]:
        """返回每个因子的 name / weight / normalized / contribution（用于解释排序）。"""
        norms = {
            "severity": _severity_norm(problem.severity),
            "volume": _volume_norm(problem.evidence_count),
            "growth": _growth_norm(growth),
            "breadth": _breadth_norm(problem.affected_segments),
        }
        factors = []
        for name, norm in norms.items():
            w = self._weights.get(name, 0.0)
            factors.append(
                {
                    "name": name,
                    "weight": w,
                    "normalized": round(norm, 4),
                    "contribution": round(w * norm, 4),
                }
            )
        return factors

    def score(self, problem: ProductProblem, growth: float = 0.5) -> float:
        return round(sum(f["contribution"] for f in self.factor_breakdown(problem, growth)), 4)

    def prioritize(
        self, problems: list[ProductProblem], growth: dict[str, float] | None = None
    ) -> list[ProductProblem]:
        """只对 confirmed 问题打分并降序排序；growth 按 problem.id 查（缺省 0.5）。"""
        growth = growth or {}
        confirmed = [p for p in problems if not p.needs_review]
        for p in confirmed:
            p.priority_score = self.score(p, growth.get(p.id, 0.5))
            p.status = ProblemStatus.PRIORITIZED
        return sorted(confirmed, key=lambda p: p.priority_score, reverse=True)
