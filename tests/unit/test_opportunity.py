"""机会生成测试。"""

from app.schemas.enums import PrimaryCategory, Severity
from app.schemas.evidence import Evidence
from app.schemas.opportunity import ProductOpportunity
from app.schemas.problem import ProductProblem
from app.services.llm import FakeLLM
from app.services.opportunity import LLMOpportunityGenerator


def _problem():
    return ProductProblem(
        title="支付失败", category=PrimaryCategory.PAYMENT_FAILED, severity=Severity.HIGH
    )


def test_generate_returns_grounded_opportunity():
    gen = LLMOpportunityGenerator(FakeLLM())
    problem = _problem()
    evidence = [Evidence(feedback_item_id="id1"), Evidence(feedback_item_id="id2")]
    texts = {"id1": "Payment failed again.", "id2": "Payment failed again."}
    opp = gen.generate(problem, evidence, texts)
    assert isinstance(opp, ProductOpportunity)
    assert opp.product_problem_id == problem.id
    assert opp.evidence_refs == ["id1", "id2"]
    assert opp.recommendation
