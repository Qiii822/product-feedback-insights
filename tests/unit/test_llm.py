"""FakeLLM / NullLLM 测试。

验证 FakeLLM 返回合法结构化输出（不依赖网络、确定性），
以及 NullLLM 会明确报错（防止误用）。
"""

import pytest

from app.schemas.analysis import FeedbackAnalysis
from app.schemas.opportunity import ProductOpportunity
from app.services.llm import FakeLLM, NullLLM


def test_fake_llm_returns_valid_analysis():
    llm = FakeLLM()
    out = llm.complete(messages=[], output_schema=FeedbackAnalysis)
    assert isinstance(out, FeedbackAnalysis)
    assert out.severity.value == "high"
    assert out.primary_category.value == "payment_failed"
    assert out.issue_type.value == "problem"


def test_fake_llm_returns_valid_opportunity():
    llm = FakeLLM()
    out = llm.complete(messages=[], output_schema=ProductOpportunity)
    assert isinstance(out, ProductOpportunity)
    assert out.recommendation


def test_fake_llm_returns_cluster_naming():
    from app.schemas.clustering import ClusterNaming

    llm = FakeLLM()
    out = llm.complete(messages=[], output_schema=ClusterNaming)
    assert isinstance(out, ClusterNaming)
    assert out.title


def test_fake_llm_rejects_unknown_schema():
    llm = FakeLLM()
    with pytest.raises(NotImplementedError):
        llm.complete(messages=[], output_schema=int)


def test_null_llm_raises_on_complete():
    llm = NullLLM()
    with pytest.raises(NotImplementedError):
        llm.complete(messages=[], output_schema=FeedbackAnalysis)


def test_deepseek_provider_requires_api_key():
    from app.core.errors import LLMProviderError
    from app.services.llm import DeepSeekProvider

    with pytest.raises(LLMProviderError):
        DeepSeekProvider("")
