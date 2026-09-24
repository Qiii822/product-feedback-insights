"""诊断（Diagnosis）数据契约。

区分三种表述，避免"把可能原因伪装成事实"：
- facts: 来自反馈/数据的直接事实（确定性、可追溯）
- hypotheses: AI 基于证据提出的可能原因（明确标注为假设，非事实）
- unknowns: 当前数据无法判断、需进一步调查的事项
"""

from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    """一个产品问题的结构化诊断。"""

    facts: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
