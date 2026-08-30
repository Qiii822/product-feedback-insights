"""自定义异常。"""


class LLMProviderError(RuntimeError):
    """LLM 供应商 / API 调用错误（网络、鉴权、限流等）。"""


class LLMOutputError(ValueError):
    """LLM 输出非法（JSON 解析失败 / schema 校验失败）。"""
