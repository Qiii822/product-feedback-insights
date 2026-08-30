"""共享枚举。

决策：severity 与 confidence 是两个不同的轴——
- severity（严重程度）是序数枚举（低/中/高/严重），回答"有多糟"。
- confidence（置信度）是连续 0~1，回答"我们有多确定"。

primary_category / issue_type 是反馈理解的分析维度，词表与
docs/product/category-taxonomy.md 保持一致。
"""

from enum import StrEnum


class Severity(StrEnum):
    """反馈 / 问题严重程度。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProblemStatus(StrEnum):
    """产品问题的处理阶段。"""

    CANDIDATE = "candidate"
    VALIDATED = "validated"
    PRIORITIZED = "prioritized"


class PrimaryCategory(StrEnum):
    """反馈理解的问题分类（11 类，flat）。

    注意：本词表必须与 docs/product/category-taxonomy.md 保持同步。
    """

    PAYMENT_DECLINED = "payment_declined"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_TIMEOUT = "payment_timeout"
    PAYMENT_METHOD_MISSING = "payment_method_missing"
    PAYMENT_METHOD_NOT_WORKING = "payment_method_not_working"
    CHECKOUT_STUCK = "checkout_stuck"
    CHECKOUT_CRASH = "checkout_crash"
    CHECKOUT_PERFORMANCE = "checkout_performance"
    DUPLICATE_CHARGE = "duplicate_charge"
    INCORRECT_CHARGE = "incorrect_charge"
    OTHER = "other"


class IssueType(StrEnum):
    """反馈类型（独立于 primary_category 的分析维度）。"""

    PROBLEM = "problem"
    REQUEST = "request"
    QUESTION = "question"
    FEEDBACK = "feedback"
