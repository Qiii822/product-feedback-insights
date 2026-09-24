"""诊断生成测试。"""

from app.schemas.diagnosis import Diagnosis
from app.schemas.enums import PrimaryCategory, Severity
from app.schemas.problem import ProductProblem
from app.services.diagnosis import LLMDiagnosisGenerator
from app.services.llm import FakeLLM


def _problem():
    return ProductProblem(
        title="支付失败",
        description="用户下单支付时失败",
        category=PrimaryCategory.PAYMENT_FAILED,
        severity=Severity.HIGH,
    )


def test_generate_returns_hypotheses_and_unknowns():
    gen = LLMDiagnosisGenerator(FakeLLM())
    d = gen.generate(_problem(), ["Payment failed again.", "Couldn't pay."])
    assert isinstance(d, Diagnosis)
    assert d.hypotheses  # 可能原因（假设）
    assert d.unknowns    # 无法判断（未知）
    assert d.facts == []  # facts 由确定性代码填充，不是 LLM
