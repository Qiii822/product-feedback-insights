"""Tracing 抽象层（Observability 的 seam）。

决策：现在只定义 `Trace` 数据结构、`Tracer` 接口，以及两个极简实现
（NullTracer / InMemoryTracer），不引入 LangSmith / OpenTelemetry 等平台。

设计目标：让"每次执行可追溯"这件事在架构上可行，而不用现在就构建
复杂的观测平台。后续替换实现（落库 / 上报外部平台）时，服务层代码不变。

记录字段（对应 Phase 0 约定）：
run_id / input / model / prompt_version / tool_calls / tool_inputs /
tool_outputs / model_output / latency_ms / token_usage / errors / final_result
"""

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Trace:
    """一次执行的完整追踪记录。"""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    input: Any = None
    model: str | None = None
    prompt_version: str | None = None
    tool_calls: list[str] = field(default_factory=list)
    tool_inputs: list[Any] = field(default_factory=list)
    tool_outputs: list[Any] = field(default_factory=list)
    model_output: Any = None
    latency_ms: float | None = None
    token_usage: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    final_result: Any = None


class Tracer(ABC):
    """追踪器接口。所有服务层组件接受可选的 Tracer。"""

    @abstractmethod
    def start_trace(self, input: Any = None) -> Trace:
        """开始一次追踪，返回 Trace 对象。"""

    @abstractmethod
    def record_llm_call(
        self,
        trace: Trace,
        *,
        model: str,
        prompt_version: str,
        input: Any,
        output: Any,
        latency_ms: float,
        token_usage: dict[str, Any] | None = None,
    ) -> None:
        """记录一次 LLM 调用。"""

    @abstractmethod
    def record_tool_call(self, trace: Trace, *, tool: str, input: Any, output: Any) -> None:
        """记录一次工具调用（当前无工具，为 Phase 6+ 预留）。"""

    @abstractmethod
    def end_trace(self, trace: Trace, *, final_result: Any = None, error: str | None = None) -> None:
        """结束追踪，记录最终结果或错误。"""


class NullTracer(Tracer):
    """空实现：不记录任何东西（默认 / 生产前的最小占位）。"""

    def start_trace(self, input: Any = None) -> Trace:
        return Trace(input=input)

    def record_llm_call(self, trace, *, model, prompt_version, input, output, latency_ms, token_usage=None):
        return None

    def record_tool_call(self, trace, *, tool, input, output):
        return None

    def end_trace(self, trace, *, final_result=None, error=None):
        return None


class InMemoryTracer(Tracer):
    """内存实现：把 trace 收集到列表，便于测试与后续落库。"""

    def __init__(self) -> None:
        self.traces: list[Trace] = []

    def start_trace(self, input: Any = None) -> Trace:
        t = Trace(input=input)
        self.traces.append(t)
        return t

    def record_llm_call(self, trace, *, model, prompt_version, input, output, latency_ms, token_usage=None):
        trace.model = model
        trace.prompt_version = prompt_version
        trace.model_output = output
        trace.latency_ms = latency_ms
        trace.token_usage = token_usage

    def record_tool_call(self, trace, *, tool, input, output):
        trace.tool_calls.append(tool)
        trace.tool_inputs.append(input)
        trace.tool_outputs.append(output)

    def end_trace(self, trace, *, final_result=None, error=None):
        trace.final_result = final_result
        if error:
            trace.errors.append(error)
