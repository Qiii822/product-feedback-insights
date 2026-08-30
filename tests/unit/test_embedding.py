"""Embedding 提供者测试。"""

from app.services.embedding import FakeEmbeddingProvider
from app.services.interfaces import EmbeddingProvider


def test_fake_embedding_is_deterministic():
    p = FakeEmbeddingProvider(dim=8)
    vecs = p.embed(["a", "a", "b"])
    assert len(vecs) == 3
    assert vecs[0] == vecs[1]  # 相同文本 → 相同向量
    assert vecs[0] != vecs[2]  # 不同文本 → 不同向量
    assert all(len(v) == 8 for v in vecs)


def test_fake_embedding_implements_provider():
    assert isinstance(FakeEmbeddingProvider(), EmbeddingProvider)
