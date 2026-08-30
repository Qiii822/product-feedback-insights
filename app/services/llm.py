"""LLM 客户端实现。

- FakeLLM / NullLLM：确定性 mock（单元测试、无网络环境）。
- DeepSeekProvider：真实 DeepSeek（OpenAI 兼容 API）。

embedding 已拆分为独立的 EmbeddingProvider（见 embedding.py）。
"""

import json
import time

from app.core.errors import LLMOutputError, LLMProviderError
from app.schemas.analysis import FeedbackAnalysis
from app.schemas.clustering import ClusterNaming
from app.schemas.opportunity import ProductOpportunity
from app.services.interfaces import LLMClient


class FakeLLM(LLMClient):
    """确定性假 LLM：不调用任何真实模型，返回固定、合法的结构化输出。"""

    def complete(self, messages, output_schema):
        if output_schema is FeedbackAnalysis:
            return FeedbackAnalysis(
                summary="(fake) 支付失败",
                primary_category="payment_failed",
                issue_type="problem",
                severity="high",
                entities=["Apple Pay"],
                confidence=0.9,
                needs_review=False,
            )
        if output_schema is ClusterNaming:
            return ClusterNaming(title="(fake) 支付问题", description="(fake) 支付相关问题")
        if output_schema is ProductOpportunity:
            return ProductOpportunity(
                title="(fake) 优化 Apple Pay 支付流程",
                recommendation="(fake) 排查 Apple Pay 收银台流程",
                confidence=0.9,
            )
        raise NotImplementedError(
            f"FakeLLM 尚未支持 schema {getattr(output_schema, '__name__', output_schema)}"
        )


class NullLLM(LLMClient):
    """空 LLM：调用即报错，防止在接入真实 provider 前被误用。"""

    def complete(self, messages, output_schema):
        raise NotImplementedError(
            "NullLLM 不会生成输出；请配置真实 provider，或在测试中使用 FakeLLM"
        )


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
    """根据配置返回 LLM 客户端：有 DEEPSEEK_API_KEY 用 DeepSeek，否则回退 FakeLLM。"""
    from app.core.config import settings

    if settings.deepseek_api_key:
        return DeepSeekProvider(settings.deepseek_api_key, model=settings.deepseek_model)
    return FakeLLM()
