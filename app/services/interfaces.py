"""核心接口定义（服务层契约）。

这些接口是系统的"替换点"，让架构在 LLM 供应商、embedding、存储、聚类算法等
维度上可替换，而业务逻辑无需改动：

- 换 LLM 供应商       → 实现 LLMClient
- 换 embedding 供应商 → 实现 EmbeddingProvider（与 LLM 独立）
- 换存储              → 实现 FeedbackRepository
- 换聚类算法          → 实现 ClusteringService

决策：使用 abc.ABC（显式抽象基类），而不是 typing.Protocol（结构化类型）。

注意：Pipeline 服务接口当前有些只有契约、没有实现，对应实现落在各 Phase。
"""

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.analysis import FeedbackAnalysis
from app.schemas.clustering import ClusteringResult
from app.schemas.evidence import Evidence
from app.schemas.feedback import FeedbackItem
from app.schemas.opportunity import ProductOpportunity
from app.schemas.problem import ProductProblem


class LLMClient(ABC):
    """LLM 客户端抽象：唯一知道"用哪家供应商"的地方（仅结构化补全）。"""

    @abstractmethod
    def complete(self, messages: list[dict[str, Any]], output_schema: type) -> Any:
        """结构化补全：返回解析为 `output_schema` 类型的对象。"""


class EmbeddingProvider(ABC):
    """Embedding 抽象：与 LLM provider 独立，便于单独替换。"""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """把文本向量化（Phase 4 聚类使用）。"""


class FeedbackRepository(ABC):
    """反馈存储抽象：唯一与存储打交道的地方。"""

    @abstractmethod
    def add(self, items: list[FeedbackItem]) -> None:
        """写入一批反馈条目。"""

    @abstractmethod
    def get(self, item_id: str) -> FeedbackItem | None:
        """按 id 读取单条反馈。"""

    @abstractmethod
    def list(self) -> list[FeedbackItem]:
        """列出全部反馈。"""

    @abstractmethod
    def get_existing_feedback_ids(self) -> set[str]:
        """返回已存在的所有 feedback_id（摄取精确去重用）。"""


class FeedbackAnalyzer(ABC):
    """反馈理解：单条反馈 → 结构化分析（Phase 3 实现）。"""

    @abstractmethod
    def analyze(self, item: FeedbackItem) -> FeedbackAnalysis:
        """分析单条反馈，返回结构化分析结果。"""


class ClusteringService(ABC):
    """问题聚类：反馈 + 分析 → 候选产品问题（Phase 4 实现）。"""

    @abstractmethod
    def cluster(
        self, items: list[FeedbackItem], analyses: list[FeedbackAnalysis]
    ) -> ClusteringResult:
        """把一组反馈聚成候选产品问题，返回问题 + 证据 + outliers。"""


class PrioritisationService(ABC):
    """优先级排序：问题列表 → 排序后的问题列表（Phase 5 实现）。"""

    @abstractmethod
    def prioritize(self, problems: list[ProductProblem]) -> list[ProductProblem]:
        """对问题列表按优先级排序（确定性打分，透明可解释）。"""


class ProductOpportunityGenerator(ABC):
    """机会生成：问题 + 证据 → 产品机会建议（Phase 5 实现）。"""

    @abstractmethod
    def generate(
        self,
        problem: ProductProblem,
        evidence: list[Evidence],
        texts: dict[str, str],
    ) -> ProductOpportunity:
        """基于问题 + 证据文本，生成可执行的建议（evidence-grounded）。"""


class EvaluationRunner(ABC):
    """评估执行器：运行评估用例并产出指标（Phase 7 实现）。"""

    @abstractmethod
    def run_case(self, case: Any) -> Any:
        """运行单个评估用例，返回评估结果。"""
