"""诊断生成（diagnosis）：问题 + 证据 → 结构化诊断（hypotheses / unknowns）。

决策：facts 由确定性代码从数据生成（见 issue_metrics.compute_facts），
LLM 只生成 hypotheses 与 unknowns，且必须 evidence-grounded——
不得把猜测伪装成事实，不得编造证据中没有的技术根因。
"""

from app.prompts.diagnosis import build_diagnosis_messages
from app.schemas.diagnosis import Diagnosis
from app.schemas.problem import ProductProblem
from app.services.interfaces import LLMClient


class LLMDiagnosisGenerator:
    """基于 LLM 的诊断生成器（单次调用，evidence-grounded）。"""

    def __init__(
        self,
        llm: LLMClient,
        *,
        model: str = "fake",
        prompt_version: str = "v1",
    ) -> None:
        self._llm = llm
        self._model = model
        self._prompt_version = prompt_version

    def generate(self, problem: ProductProblem, evidence_texts: list[str]) -> Diagnosis:
        messages = build_diagnosis_messages(problem, evidence_texts)
        draft = self._llm.complete(messages, Diagnosis)
        return Diagnosis(
            hypotheses=draft.hypotheses,
            unknowns=draft.unknowns,
        )
