"""评估 runner：把 production pipeline 当黑盒运行，计算指标，产出报告。

- 分类 / 命名 / confidence 依赖 LLM：可传入真实 provider（DeepSeek）或 FakeLLM。
- 聚类（真实 embedding）与 prioritisation（确定性）不依赖 LLM。
"""

from app.evaluation import cases as case_loader
from app.evaluation.metrics import (
    accuracy,
    adjusted_rand_index,
    macro_f1,
    pairwise_prf,
    per_label_prf,
    spearman_between_orders,
    top_k_overlap,
)
from app.schemas.enums import Severity
from app.schemas.feedback import FeedbackItem
from app.schemas.problem import ProductProblem
from app.services.analyzer import LLMFeedbackAnalyzer
from app.services.clustering import agglomerative_cluster
from app.services.embedding import FastembedEmbeddingProvider
from app.services.llm import FakeLLM
from app.services.prioritisation import WeightedPrioritisationService

CLUSTER_THRESHOLDS = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90]


def _histogram(values: list[float]) -> dict:
    buckets = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    return {f"{lo:.1f}-{hi:.1f}": sum(1 for v in values if lo <= v < hi) for lo, hi in buckets}


def run_classification(llm=None, model: str = "fake") -> dict:
    llm = llm or FakeLLM()
    cases = case_loader.load_classification_cases()
    analyzer = LLMFeedbackAnalyzer(llm, model=model, prompt_version="v1")

    true_cat, pred_cat = [], []
    true_it, pred_it = [], []
    confidences, needs_review_flags = [], []
    failures = []
    for c in cases:
        item = FeedbackItem(feedback_id=c["id"], raw_text=c["raw_text"])
        a = analyzer.analyze(item)
        true_cat.append(c["expected_category"])
        pred_cat.append(a.primary_category.value)
        true_it.append(c["expected_issue_type"])
        pred_it.append(a.issue_type.value)
        confidences.append(a.confidence)
        needs_review_flags.append(a.needs_review)
        if a.primary_category.value != c["expected_category"]:
            failures.append(
                {
                    "id": c["id"],
                    "raw_text": c["raw_text"],
                    "expected": c["expected_category"],
                    "predicted": a.primary_category.value,
                    "confidence": a.confidence,
                    "needs_review": a.needs_review,
                }
            )

    labels = sorted(set(true_cat))
    confs = sorted(confidences)
    return {
        "n": len(cases),
        "accuracy": round(accuracy(true_cat, pred_cat), 4),
        "macro_f1": round(macro_f1(true_cat, pred_cat, labels), 4),
        "issue_type_accuracy": round(accuracy(true_it, pred_it), 4),
        "other_rate": round(sum(p == "other" for p in pred_cat) / len(pred_cat), 4),
        "true_other_rate": round(sum(t == "other" for t in true_cat) / len(true_cat), 4),
        "needs_review_rate": round(sum(needs_review_flags) / len(needs_review_flags), 4),
        "confidence": {
            "min": round(confs[0], 4) if confs else None,
            "mean": round(sum(confs) / len(confs), 4) if confs else None,
            "max": round(confs[-1], 4) if confs else None,
            "histogram": _histogram(confidences),
        },
        "per_category": {
            l: [round(x, 3) for x in per_label_prf(true_cat, pred_cat, labels)[l]]
            for l in labels
        },
        "failure_count": len(failures),
        "failures": failures[:15],
    }


def run_clustering() -> dict:
    cases = case_loader.load_clustering_cases()
    embedder = FastembedEmbeddingProvider()
    texts = [c["raw_text"] for c in cases]
    embeddings = embedder.embed(texts)
    true_labels = [c["problem_id"] for c in cases]
    idx = {c["id"]: i for i, c in enumerate(cases)}

    thresholds = {}
    failure_merged = {}
    for t in CLUSTER_THRESHOLDS:
        labels = agglomerative_cluster(embeddings, t)
        pred = [f"c{lab}" if lab >= 0 else f"o{i}" for i, lab in enumerate(labels)]
        p, r, f1 = pairwise_prf(true_labels, pred)
        thresholds[t] = {
            "pairwise_precision": round(p, 4),
            "pairwise_recall": round(r, 4),
            "pairwise_f1": round(f1, 4),
            "ari": round(adjusted_rand_index(true_labels, pred), 4),
        }
        lab_frozen, lab_failed = labels[idx["k006"]], labels[idx["k001"]]
        failure_merged[t] = bool(lab_frozen != -1 and lab_frozen == lab_failed)

    return {"n": len(cases), "thresholds": thresholds, "failure_merged": failure_merged}


def run_prioritisation() -> dict:
    data = case_loader.load_prioritisation_cases()
    problems = [
        ProductProblem(
            id=p["id"],
            title=p["title"],
            severity=Severity(p["severity"]),
            affected_segments=p["segments"],
            evidence_count=p["evidence_count"],
        )
        for p in data["problems"]
    ]
    ranked = WeightedPrioritisationService().prioritize(problems)
    system_order = [p.id for p in ranked]
    human_order = data["human_order"]
    return {
        "top1_agreement": 1.0 if system_order[0] == human_order[0] else 0.0,
        "top3_overlap": round(top_k_overlap(human_order, system_order, 3), 4),
        "spearman": round(spearman_between_orders(human_order, system_order), 4),
        "system_order": system_order,
        "human_order": human_order,
    }


def run_all() -> dict:
    return {
        "classification": run_classification(),
        "clustering": run_clustering(),
        "prioritisation": run_prioritisation(),
    }
