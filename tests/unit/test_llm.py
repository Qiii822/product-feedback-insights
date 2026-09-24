"""get_llm / DeepSeekProvider 测试。"""

import pytest

from app.core.errors import LLMProviderError
from app.services.llm import DeepSeekProvider, get_llm


def test_deepseek_provider_requires_api_key():
    with pytest.raises(LLMProviderError):
        DeepSeekProvider("")


def test_get_llm_raises_without_api_key(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "deepseek_api_key", None)
    with pytest.raises(LLMProviderError):
        get_llm()
