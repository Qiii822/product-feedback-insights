"""ORM 模型。

命名约定：ORM 模型加 `Model` 后缀（如 FeedbackItemModel），
以区别于 app/schemas 中的同名 Pydantic schema（如 FeedbackItem）。
"""

from app.models.evidence import EvidenceModel
from app.models.feedback import FeedbackItemModel
from app.models.opportunity import ProductOpportunityModel
from app.models.problem import ProductProblemModel

__all__ = [
    "FeedbackItemModel",
    "ProductProblemModel",
    "EvidenceModel",
    "ProductOpportunityModel",
]
