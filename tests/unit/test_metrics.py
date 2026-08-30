"""评估指标测试。"""

from app.evaluation.metrics import (
    accuracy,
    adjusted_rand_index,
    macro_f1,
    pairwise_prf,
    spearman_between_orders,
    top_k_overlap,
)


def test_accuracy():
    assert accuracy(["a", "b", "a"], ["a", "a", "a"]) == 2 / 3
    assert accuracy([], []) == 0.0


def test_macro_f1_perfect_and_zero():
    assert macro_f1(["a", "b"], ["a", "b"], ["a", "b"]) == 1.0
    assert macro_f1(["a", "b"], ["b", "a"], ["a", "b"]) == 0.0


def test_pairwise_prf_perfect_cluster():
    # 真值：0,1 同簇；2,3 同簇。预测完全一致。
    true = [0, 0, 1, 1]
    pred = [0, 0, 1, 1]
    p, r, f1 = pairwise_prf(true, pred)
    assert (p, r, f1) == (1.0, 1.0, 1.0)


def test_pairwise_prf_over_merge():
    # 真值两簇；预测把四个全聚一起 → 精确率低、召回率高
    true = [0, 0, 1, 1]
    pred = [0, 0, 0, 0]
    p, r, _ = pairwise_prf(true, pred)
    assert p == 2 / 6  # 真同簇对只有 2 个（(0,1),(2,3)），预测同簇对 6 个
    assert r == 1.0


def test_adjusted_rand_index_perfect():
    assert adjusted_rand_index([0, 0, 1, 1], [0, 0, 1, 1]) == 1.0


def test_adjusted_rand_index_independent():
    # 完全随机（交换后）→ ARI 应为负或接近 0
    ari = adjusted_rand_index([0, 0, 1, 1], [0, 1, 0, 1])
    assert ari < 0.2


def test_spearman_perfect_and_reversed():
    assert spearman_between_orders(["a", "b", "c"], ["a", "b", "c"]) == 1.0
    assert spearman_between_orders(["a", "b", "c"], ["c", "b", "a"]) == -1.0


def test_top_k_overlap():
    assert top_k_overlap(["a", "b", "c"], ["a", "x", "c"], 3) == 2 / 3
