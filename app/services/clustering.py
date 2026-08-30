"""问题聚类（clustering）：反馈 + 分析 → 候选产品问题。

算法（Phase 4）：
真实 embedding → 余弦相似度 → 凝聚聚类（complete linkage，precision-over-recall）
→ 区分 confirmed（多成员簇）/ candidate（单成员簇）→ LLM 命名（evidence-grounded）
→ 组装 ProductProblem + Evidence。

关键决策：
- complete linkage = 仅当两簇间所有对的相似度都 ≥ 阈值才合并，最保守。
- 单成员簇不再被静默丢弃，而是作为 candidate problem（needs_review=True）保留。
- cohesion_score 是确定性计算的簇内语义一致度（平均到质心相似度）。
- confidence 是 provisional 占位（未校准，不用于产品决策）。
- affected_segments 从 FeedbackItem.platform 元数据聚合，不是 LLM 推断。

已知限制（Phase 4 review）：
- 当前聚类只依赖 embedding 相似度，未考虑 primary_category compatibility。
  已知失败案例："Payment page froze."（checkout_stuck）被并入 payment_failed 簇
  （cosine ≥ 0.75）。已记录到 data/eval/known_failures.md，Phase 7 引入
  category-aware 聚类（semantic similarity + primary_category compatibility）并加入评估集。
"""

from collections import Counter

import numpy as np

from app.prompts.naming import build_naming_messages
from app.schemas.analysis import FeedbackAnalysis
from app.schemas.clustering import ClusterNaming, ClusteringResult
from app.schemas.enums import PrimaryCategory, Severity
from app.schemas.evidence import Evidence
from app.schemas.feedback import FeedbackItem
from app.schemas.problem import ProductProblem
from app.services.interfaces import ClusteringService, EmbeddingProvider, LLMClient

_SEVERITY_RANK = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


def cosine_similarity_matrix(embeddings: list[list[float]]) -> np.ndarray:
    """计算两两余弦相似度矩阵（先归一化再点积）。"""
    M = np.asarray(embeddings, dtype=np.float64)
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    M = M / norms
    return M @ M.T


def agglomerative_cluster(embeddings: list[list[float]], threshold: float) -> list[int]:
    """凝聚聚类（complete linkage）。

    返回 labels：每个 item 的簇 id（从 0 起），-1 表示单成员（未与其他条目达到阈值）。
    """
    n = len(embeddings)
    if n == 0:
        return []
    if n == 1:
        return [-1]

    sim = cosine_similarity_matrix(embeddings)
    clusters = [{i} for i in range(n)]

    while len(clusters) > 1:
        best = (-1, -1, -1.0)
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # complete linkage：簇间相似度 = 所有跨簇对的最小值
                s = min(sim[a, b] for a in clusters[i] for b in clusters[j])
                if s > best[2]:
                    best = (i, j, s)
        if best[2] < threshold:
            break
        i, j, _ = best
        clusters[i] = clusters[i] | clusters[j]
        del clusters[j]

    labels = [-1] * n
    cid = 0
    for cluster in clusters:
        if len(cluster) >= 2:
            for idx in cluster:
                labels[idx] = cid
            cid += 1
    return labels


class EmbeddingClusteringService(ClusteringService):
    """基于 embedding + 相似度阈值 + LLM 命名的聚类服务。"""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        llm: LLMClient,
        *,
        threshold: float = 0.75,
        model: str = "fake",
        naming_prompt_version: str = "v1",
    ) -> None:
        self._embedder = embedder
        self._llm = llm
        self._threshold = threshold
        self._model = model
        self._naming_prompt_version = naming_prompt_version

    def cluster(self, items, analyses) -> ClusteringResult:
        analysis_by_item = {a.feedback_item_id: a for a in analyses}

        # 分离 other（不参与聚类，但统计）
        to_cluster: list[tuple[FeedbackItem, FeedbackAnalysis]] = []
        other_samples: list[FeedbackItem] = []
        for item in items:
            a = analysis_by_item.get(item.id)
            if a is None:
                continue  # 无分析，跳过
            if a.primary_category is PrimaryCategory.OTHER:
                other_samples.append(item)
            else:
                to_cluster.append((item, a))

        texts = [item.raw_text for item, _ in to_cluster]
        embeddings = self._embedder.embed(texts)
        labels = agglomerative_cluster(embeddings, self._threshold)

        # 分组：多成员簇（confirmed）vs 单成员（candidate）
        cluster_groups: dict[int, list] = {}
        singletons: list = []
        for (item, a), emb, label in zip(to_cluster, embeddings, labels):
            if label == -1:
                singletons.append((item, a, emb))
            else:
                cluster_groups.setdefault(label, []).append((item, a, emb))

        problems, evidence = [], []
        for members in cluster_groups.values():
            problem, evs = self._build_problem(members)
            problems.append(problem)
            evidence.extend(evs)
        for member in singletons:
            problem, evs = self._build_problem([member])
            problems.append(problem)
            evidence.extend(evs)

        total = len(items)
        other_count = len(other_samples)
        return ClusteringResult(
            problems=problems,
            evidence=evidence,
            other_count=other_count,
            other_percentage=(other_count / total * 100) if total else 0.0,
            other_samples=[item.raw_text for item in other_samples[:3]],
        )

    def _build_problem(self, members):
        """把一组 (item, analysis, embedding) 组装成 ProductProblem + Evidence。"""
        representative = [item.raw_text for item, _, _ in members[:3]]
        naming = self._llm.complete(build_naming_messages(representative), ClusterNaming)

        category = Counter(a.primary_category for _, a, _ in members).most_common(1)[0][0]
        severity = max(
            (a.severity for _, a, _ in members), key=lambda s: _SEVERITY_RANK[s]
        )
        platforms = [item.platform for item, _, _ in members if item.platform]
        affected = [p for p, _ in Counter(platforms).most_common()]
        needs_review = len(members) == 1

        # cohesion：簇内平均到质心的相似度（单成员无意义，记 0.0）
        cohesion = 0.0
        relevances: list[float] = []
        if len(members) >= 2:
            centroid = np.mean([np.asarray(emb) for _, _, emb in members], axis=0)
            for _, _, emb in members:
                emb_arr = np.asarray(emb)
                denom = (float(np.linalg.norm(emb_arr)) * float(np.linalg.norm(centroid))) or 1.0
                relevances.append(float(np.dot(emb_arr, centroid) / denom))
            cohesion = sum(relevances) / len(relevances)

        problem = ProductProblem(
            title=naming.title,
            description=naming.description,
            category=category,
            severity=severity,
            affected_segments=affected,
            confidence=0.5,  # provisional 占位（未校准，不用于产品决策）
            cohesion_score=round(cohesion, 4),
            needs_review=needs_review,
            evidence_count=len(members),
        )

        evidence = []
        for idx, (item, a, _) in enumerate(members):
            relevance = relevances[idx] if relevances else 1.0
            evidence.append(
                Evidence(
                    product_problem_id=problem.id,
                    feedback_item_id=item.id,
                    analysis_id=a.id,
                    relevance_score=round(max(0.0, min(1.0, relevance)), 4),
                )
            )
        return problem, evidence
