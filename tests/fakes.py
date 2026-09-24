"""测试专用 mock LLM（不进入生产）。

生产只允许真实 provider（见 app/services/llm.py）；此处提供一个确定性
mock，让单元测试在不调用网络的前提下验证 analyzer / clustering /
opportunity / diagnosis 等确定性逻辑与 schema 契约。
"""

from app.schemas.analysis import FeedbackAnalysis
from app.schemas.clustering import ClusterNaming
from app.schemas.diagnosis import Diagnosis
from app.schemas.enums import IssueType, PrimaryCategory, Severity
from app.schemas.opportunity import ProductOpportunity
from app.services.interfaces import LLMClient


class FakeLLM(LLMClient):
    """确定性 mock：对每个 schema 返回固定但合法的结构化输出。"""

    def complete(self, messages, output_schema):
        if output_schema is FeedbackAnalysis:
            return FeedbackAnalysis(
                summary="支付失败",
                primary_category=PrimaryCategory.PAYMENT_FAILED,
                issue_type=IssueType.PROBLEM,
                severity=Severity.HIGH,
                entities=["Payment"],
                confidence=0.9,
                needs_review=False,
            )
        if output_schema is ClusterNaming:
            return ClusterNaming(title="支付问题", description="支付相关反馈")
        if output_schema is Diagnosis:
            return Diagnosis(
                hypotheses=["可能是支付流程出现的问题"],
                unknowns=["当前数据无法判断根因"],
            )
        if output_schema is ProductOpportunity:
            return ProductOpportunity(
                title="优化支付流程",
                recommendation="排查支付失败",
                action_items=["定位失败环节"],
                success_metrics=["失败率下降"],
            )
        raise NotImplementedError(f"FakeLLM 不支持 schema {getattr(output_schema, '__name__', output_schema)}")
