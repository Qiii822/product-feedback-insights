# 已知聚类失败案例（待进入 Phase 7 evaluation set）

> 记录 Phase 4 demo 中发现的失败案例，作为 Phase 7 评估集与聚类算法改进的依据。

## Case 1：embedding-only 聚类导致分类冲突

- **输入反馈**："Payment page froze."
- **期望 primary_category**：`checkout_stuck`（taxonomy 已区分 `payment_failed` 与 `checkout_stuck`）
- **实际聚类结果**：被并入了 `payment_failed` 簇（因为 "Payment page froze." 与 "Payment failed again." 的 embedding 余弦相似度 ≥ 0.75）
- **根因**：当前聚类只依赖 embedding 相似度，未考虑 `primary_category` compatibility（semantic similarity + category 的一致性）。
- **记录日期**：2026-08-30
- **后续动作**：Phase 7 引入 category-aware 聚类（semantic similarity + primary_category compatibility），并将本案例加入评估集验证。
- **当前阈值状态**：0.75 是 initial heuristic，**不是** validated production threshold，将在 Phase 7 用标注评估集校准。
