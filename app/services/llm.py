"""LLM 客户端实现。

- DeepSeekProvider：真实 DeepSeek（OpenAI 兼容 API）。
- get_llm()：未配置 DEEPSEEK_API_KEY 时抛 LLMProviderError（生产不静默回退 mock）。

embedding 已拆分为独立的 EmbeddingProvider（见 embedding.py）。
测试专用的 mock LLM 见 tests/fakes.py（不进入生产）。
"""

import json
import time

from app.core.errors import LLMOutputError, LLMProviderError
from app.services.interfaces import LLMClient


class DeepSeekProvider(LLMClient):
    """真实 DeepSeek LLM（OpenAI 兼容 API）。

    结构化输出：JSON 模式 + Pydantic schema 校验。
    - JSON 解析失败 / schema 校验失败 → 抛 LLMOutputError（绝不静默转成合法数据）。
    - API / 网络 / 鉴权错误 → 抛 LLMProviderError。
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.0,
    ) -> None:
        if not api_key:
            raise LLMProviderError("DEEPSEEK_API_KEY 未设置")
        from openai import OpenAI  # 惰性导入，测试环境不加载

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature
        # 可观测性：累计本次会话的 token / 延迟 / 调用次数
        self.total_tokens = 0
        self.total_calls = 0
        self.total_latency_ms = 0.0

    def complete(self, messages, output_schema):
        from pydantic import ValidationError

        started = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=self._temperature,
            )
        except Exception as exc:
            raise LLMProviderError(f"DeepSeek API 调用失败：{exc}") from exc

        self.total_latency_ms += (time.perf_counter() - started) * 1000
        self.total_calls += 1
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.total_tokens += int(getattr(usage, "total_tokens", 0) or 0)

        content = (resp.choices[0].message.content or "").strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMOutputError(f"LLM 返回了无法解析的 JSON：{content[:200]!r}") from exc

        try:
            return output_schema.model_validate(data)
        except ValidationError as exc:
            raise LLMOutputError(f"LLM 输出不符合 schema：{exc}") from exc


def get_llm() -> LLMClient:
    """根据配置返回 DeepSeek 客户端；未配置 DEEPSEEK_API_KEY 时抛错（不静默回退 mock）。"""
    from app.core.config import settings

    if not settings.deepseek_api_key:
        raise LLMProviderError("DEEPSEEK_API_KEY 未设置：请在 .env 中配置后重试")
    return DeepSeekProvider(settings.deepseek_api_key, model=settings.deepseek_model)
