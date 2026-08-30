"""Tracing 抽象测试。

验证 InMemoryTracer 能记录一条完整 trace 的关键字段，
以及 NullTracer 可安全调用（不报错、不记录）。
"""

from app.core.tracing import InMemoryTracer, NullTracer


def test_inmemory_tracer_records_trace():
    tracer = InMemoryTracer()
    trace = tracer.start_trace(input="Payment failed again.")
    tracer.record_llm_call(
        trace,
        model="fake",
        prompt_version="v1",
        input="hello",
        output="ok",
        latency_ms=12.3,
        token_usage={"input": 5, "output": 3},
    )
    tracer.end_trace(trace, final_result="done")

    assert len(tracer.traces) == 1
    assert trace.model == "fake"
    assert trace.prompt_version == "v1"
    assert trace.latency_ms == 12.3
    assert trace.final_result == "done"


def test_inmemory_tracer_records_error():
    tracer = InMemoryTracer()
    trace = tracer.start_trace(input="x")
    tracer.end_trace(trace, error="something broke")
    assert trace.errors == ["something broke"]


def test_null_tracer_is_safe_noop():
    tracer = NullTracer()
    trace = tracer.start_trace(input="x")
    tracer.record_llm_call(
        trace, model="m", prompt_version="v", input="i", output="o", latency_ms=0
    )
    tracer.end_trace(trace, final_result="done")
    # 不抛异常即可
