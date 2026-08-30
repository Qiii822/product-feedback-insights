"""Embedding 提供者实现。

决策（Phase 4）：embedding 与 LLM 分离为独立抽象，便于单独替换。
- FastembedEmbeddingProvider：真实本地 embedding（fastembed + ONNX），无 API key。
- FakeEmbeddingProvider：确定性伪向量，仅用于单元测试（不用于评估真实聚类质量）。
"""

import math

from app.services.interfaces import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """确定性伪 embedding（仅测试用；相同文本 → 相同向量）。"""

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    def embed(self, texts):
        out = []
        for text in texts:
            h = abs(hash(text))
            vec = [((h >> (i * 4)) & 0xF) / 15.0 for i in range(self._dim)]
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            out.append([x / norm for x in vec])
        return out


class FastembedEmbeddingProvider(EmbeddingProvider):
    """真实本地 embedding（fastembed，ONNX）。

    首次实例化会从 Hugging Face Hub 下载模型（约 100MB）。
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        from fastembed import TextEmbedding  # 惰性导入，避免测试时加载

        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts):
        if not texts:
            return []
        return [list(map(float, v)) for v in self._model.embed(texts)]
