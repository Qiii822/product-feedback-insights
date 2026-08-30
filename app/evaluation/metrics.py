"""评估指标（纯函数，无副作用，可独立测试）。

所有指标是确定性计算，不依赖 LLM（grader 确定性优先；LLM-as-judge 单独处理）。
"""

from collections import Counter
from math import comb


def accuracy(true: list, pred: list) -> float:
    if not true:
        return 0.0
    return sum(t == p for t, p in zip(true, pred)) / len(true)


def precision_recall_f1(true: list, pred: list, label) -> tuple[float, float, float]:
    tp = sum(1 for t, p in zip(true, pred) if t == label and p == label)
    fp = sum(1 for t, p in zip(true, pred) if t != label and p == label)
    fn = sum(1 for t, p in zip(true, pred) if t == label and p != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def macro_f1(true: list, pred: list, labels: list) -> float:
    if not labels:
        return 0.0
    return sum(precision_recall_f1(true, pred, l)[2] for l in labels) / len(labels)


def per_label_prf(true: list, pred: list, labels: list) -> dict:
    return {l: precision_recall_f1(true, pred, l) for l in labels}


def pairwise_same(labels: list) -> set:
    pairs = set()
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            if labels[i] == labels[j]:
                pairs.add((i, j))
    return pairs


def pairwise_prf(true_labels: list, pred_labels: list) -> tuple[float, float, float]:
    """聚类 pairwise 精确率/召回率/F1（同簇为正例）。"""
    true_pairs = pairwise_same(true_labels)
    pred_pairs = pairwise_same(pred_labels)
    tp = len(true_pairs & pred_pairs)
    fp = len(pred_pairs - true_pairs)
    fn = len(true_pairs - pred_pairs)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def adjusted_rand_index(true_labels: list, pred_labels: list) -> float:
    """标准调整兰德指数（ARI）。"""
    n = len(true_labels)
    if n <= 1:
        return 1.0
    true_ids = {v: i for i, v in enumerate(sorted(set(true_labels)))}
    pred_ids = {v: i for i, v in enumerate(sorted(set(pred_labels)))}
    contingency = Counter()
    for t, p in zip(true_labels, pred_labels):
        contingency[(true_ids[t], pred_ids[p])] += 1
    row_sums = Counter()
    col_sums = Counter()
    for (i, j), c in contingency.items():
        row_sums[i] += c
        col_sums[j] += c

    sum_comb = sum(comb(c, 2) for c in contingency.values())
    sum_row = sum(comb(c, 2) for c in row_sums.values())
    sum_col = sum(comb(c, 2) for c in col_sums.values())
    total = comb(n, 2)
    expected = (sum_row * sum_col) / total if total else 0.0
    max_index = 0.5 * (sum_row + sum_col)
    if max_index - expected == 0:
        return 0.0
    return (sum_comb - expected) / (max_index - expected)


def spearman_between_orders(order_a: list, order_b: list) -> float:
    """两个排序（同一组元素，best first）之间的 Spearman 秩相关系数（无并列假设）。"""
    ids = list(order_a)
    rank_a = {pid: i for i, pid in enumerate(order_a)}
    rank_b = {pid: i for i, pid in enumerate(order_b)}
    n = len(ids)
    if n <= 1:
        return 1.0
    d2 = sum((rank_a[i] - rank_b[i]) ** 2 for i in ids)
    return 1 - 6 * d2 / (n * (n * n - 1))


def top_k_overlap(order_a: list, order_b: list, k: int) -> float:
    """top-k 交集比例。"""
    if not order_a or not order_b:
        return 0.0
    k = min(k, len(order_a), len(order_b))
    return len(set(order_a[:k]) & set(order_b[:k])) / k
