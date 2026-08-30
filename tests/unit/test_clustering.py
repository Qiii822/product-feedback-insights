"""聚类测试。"""

from app.schemas.analysis import FeedbackAnalysis
from app.schemas.enums import IssueType, PrimaryCategory, Severity
from app.schemas.feedback import FeedbackItem
from app.services.clustering import EmbeddingClusteringService, agglomerative_cluster
from app.services.llm import FakeLLM


def test_agglomerative_groups_identical_and_flags_singleton():
    # [1,0] 与 [1,0] 相同 → 聚为一簇；[0,1] 正交 → 单成员（-1）
    labels = agglomerative_cluster([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], threshold=0.9)
    assert labels[0] == labels[1]
    assert labels[2] == -1


class _StubEmbedder:
    """确定性 stub：相同文本 → 相同向量，不同文本 → 正交。"""

    _map = {"Payment failed": [1.0, 0.0, 0.0], "Checkout stuck": [0.0, 1.0, 0.0]}

    def embed(self, texts):
        return [self._map.get(t, [0.0, 0.0, 1.0]) for t in texts]


def _item(feedback_id, raw_text):
    return FeedbackItem(feedback_id=feedback_id, raw_text=raw_text)


def _analysis(item, category=PrimaryCategory.PAYMENT_FAILED, issue_type=IssueType.PROBLEM):
    return FeedbackAnalysis(
        feedback_item_id=item.id,
        summary="x",
        primary_category=category,
        issue_type=issue_type,
        severity=Severity.HIGH,
        confidence=0.9,
    )


def test_clustering_service_confirmed_vs_candidate():
    items = [
        _item("fb_1", "Payment failed"),
        _item("fb_2", "Payment failed"),
        _item("fb_3", "Checkout stuck"),
    ]
    analyses = [_analysis(i) for i in items]

    service = EmbeddingClusteringService(_StubEmbedder(), FakeLLM(), threshold=0.9)
    result = service.cluster(items, analyses)

    assert len(result.problems) == 2  # 1 confirmed + 1 candidate
    confirmed = [p for p in result.problems if not p.needs_review]
    candidates = [p for p in result.problems if p.needs_review]
    assert len(confirmed) == 1
    assert confirmed[0].evidence_count == 2
    assert confirmed[0].cohesion_score == 1.0  # 两条相同向量 → 内聚度 1.0
    assert len(candidates) == 1
    assert candidates[0].evidence_count == 1
    assert len(result.evidence) == 3  # 2 条 confirmed + 1 条 candidate


def test_clustering_excludes_other_and_counts():
    items = [
        _item("fb_1", "Payment failed"),
        _item("fb_2", "Payment failed"),
        _item("fb_3", "I want a refund"),
    ]
    analyses = [_analysis(i) for i in items[:2]]
    analyses.append(
        _analysis(items[2], category=PrimaryCategory.OTHER, issue_type=IssueType.REQUEST)
    )

    service = EmbeddingClusteringService(_StubEmbedder(), FakeLLM(), threshold=0.9)
    result = service.cluster(items, analyses)

    assert len(result.problems) == 1
    assert result.other_count == 1
    assert abs(result.other_percentage - 100 / 3) < 0.01
    assert result.other_samples == ["I want a refund"]
