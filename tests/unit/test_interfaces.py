"""接口契约测试。

验证：抽象基类不可实例化（未实现即报错），以及 Fake/InMemory 实现
确实"实现了"对应接口。
"""

import pytest

from app.repositories.memory import InMemoryFeedbackRepository
from app.services.interfaces import (
    LLMClient,
    ClusteringService,
    FeedbackAnalyzer,
    FeedbackRepository,
    PrioritisationService,
)
from app.services.llm import FakeLLM


def test_llm_client_is_abstract():
    with pytest.raises(TypeError):
        LLMClient()


def test_feedback_analyzer_is_abstract():
    with pytest.raises(TypeError):
        FeedbackAnalyzer()


def test_clustering_service_is_abstract():
    with pytest.raises(TypeError):
        ClusteringService()


def test_prioritisation_service_is_abstract():
    with pytest.raises(TypeError):
        PrioritisationService()


def test_fake_llm_implements_llm_client():
    llm = FakeLLM()
    assert isinstance(llm, LLMClient)


def test_inmemory_repo_implements_feedback_repository():
    repo = InMemoryFeedbackRepository()
    assert isinstance(repo, FeedbackRepository)
