"""Pydantic 数据契约。

这里的 schema 是系统的"领域数据类型"，同时承担 LLM 结构化输出的校验契约：
LLM 返回的 JSON 必须能被解析成这里的对象，否则视为非法输出（Phase 3 强制）。
"""

from app.schemas.analysis import FeedbackAnalysis
from app.schemas.clustering import ClusteringResult, ClusterNaming
from app.schemas.enums import IssueType, PrimaryCategory, ProblemStatus, Severity
from app.schemas.evidence import Evidence
from app.schemas.feedback import FeedbackItem
from app.schemas.ingestion import IngestionResult
from app.schemas.opportunity import ProductOpportunity
from app.schemas.problem import ProductProblem

__all__ = [
    "FeedbackItem",
    "FeedbackAnalysis",
    "ProductProblem",
    "Evidence",
    "ProductOpportunity",
    "IngestionResult",
    "ClusteringResult",
    "ClusterNaming",
    "Severity",
    "ProblemStatus",
    "PrimaryCategory",
    "IssueType",
]
