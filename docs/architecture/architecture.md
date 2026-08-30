# 架构文档

> 本文描述当前（Phase 1）的架构设计与关键决策。完整规划见仓库根目录 `PHASE-0.md`。

## 1. 一句话总览

本系统是一条由 **「确定性步骤 + 单次 LLM 调用」** 组成的**流水线（pipeline）**，而非自主 Agent。

```
文件 (CSV/JSON)
  → 摄取 (解析 → 归一化 → 精确去重 → 持久化) → FeedbackItem
  → 反馈理解 (FeedbackAnalyzer, 单次 LLM 调用) → FeedbackAnalysis
  → 问题聚类 (ClusteringService, 确定性) → ProductProblem[] + Evidence[]
  → 优先级排序 (PrioritisationService, 确定性) → 排序后的 ProductProblem[]
  → 机会生成 (ProductOpportunityGenerator, 单次 LLM 调用) → ProductOpportunity
```

## 2. 关键决策：Pipeline-first，而非 Agent

**决策**：当前 MVP 采用固定流水线架构，不引入自主 Agent。

**备选方案**：Agentic loop（LLM 自主选择工具、观察结果、迭代推理）。

**权衡**：
- Pipeline：步骤固定、顺序已知、可解释、可逐段测试；缺点是无法动态适应。
- Agent：能动态决策、迭代；但引入不确定性、更难评估与调试，且当前无明确需求。

**为什么选 Pipeline**：MVP 的五个阶段都不需要"决定下一步做什么"。当确定性 Pipeline 实现并完成 Evaluation 后，再依据实际数据判断哪些环节真正需要 Agentic 行为（Phase 6）。这是一个**当前阶段的架构决策，不是永久限制**。

## 3. 分层与依赖方向

```
        ┌─────────────┐
        │   api/      │   HTTP 路由（对外接口）
        └──────┬──────┘
               │ 依赖（接口，不依赖实现）
        ┌──────▼──────────────┐
        │  services/interfaces │  业务契约（抽象基类）
        └──────┬──────────────┘
      ┌────────┴─────────┐
      │ services/llm.py  │  repositories/memory.py   ← 具体实现（可替换）
      └──────────────────┘

   schemas/  ← 被所有层共享（纯数据契约，无依赖）
   core/     ← 被所有层共享（config / logging / tracing）
   db/ + models/  ← 持久化层（Phase 2 接入 repository 的 SQL 实现）
```

**依赖规则**：上层只依赖**接口**，不依赖具体实现。因此换 LLM 供应商、换存储、换聚类算法，都不需要改动上层业务逻辑。

## 4. 替换点（接口）

| 接口 | 替换对象 | 当前实现 | 后续实现 |
|------|----------|----------|----------|
| `LLMClient` | LLM 供应商 | `FakeLLM` / `NullLLM` | Anthropic / OpenAI |
| `FeedbackRepository` | 存储 | `InMemoryFeedbackRepository` | SQLAlchemy 版（Phase 2） |
| `FeedbackAnalyzer` | 反馈理解 | —（契约） | Phase 3 |
| `ClusteringService` | 聚类算法 | —（契约） | Phase 4 |
| `PrioritisationService` | 排序打分 | —（契约） | Phase 5 |
| `ProductOpportunityGenerator` | 建议生成 | —（契约） | Phase 5 |
| `EvaluationRunner` | 评估执行 | —（契约） | Phase 7 |
| `Tracer`（core/tracing.py） | 追踪后端 | `InMemoryTracer` / `NullTracer` | LangSmith 等 |

## 5. 五个数据契约的关系

```
FeedbackItem ──1:1──> FeedbackAnalysis ──N:1──> ProductProblem
                          │                        ▲
                          └──────── Evidence ──────┘
                                                   │
                              ProductOpportunity ──┘  (引用 Evidence)
```

- `FeedbackAnalysis` 关联一条 `FeedbackItem`（`feedback_item_id`）。
- `ProductProblem` 由多条 `FeedbackAnalysis` 聚类而成。
- `Evidence` 显式记录「哪条反馈支撑了哪个问题」，保证问题**可追溯到原始证据**。
- `ProductOpportunity` 通过 `evidence_refs` 引用反馈，是后续度量**幻觉率**的基础。

## 6. 可观测性 seam

`core/tracing.py` 定义 `Trace` 与 `Tracer` 接口，记录：`run_id / input / model / prompt_version / tool_calls / tool_inputs / tool_outputs / model_output / latency_ms / token_usage / errors / final_result`。

当前只提供 `NullTracer`（不记录）与 `InMemoryTracer`（内存收集）。后续接入外部平台时，服务层代码不变——这是 seam 的意义。

## 7. 评估预留

`EvaluationRunner` 接口已锁定（见 `services/interfaces.py`）。Phase 7 将实现：
- 评估用例（输入反馈 + 期望分类/证据/严重程度/结果）
- 确定性 grader 优先，LLM-as-a-judge 仅在确定性不足时使用
- 指标计算与失败定位

## 8. 摄取层（Phase 2）

数据入口：`app/services/ingestion.py` + `app/services/normalization.py`。

```
parse_file (CSV/JSON)
  → normalize_row（校验 + 归一化）
  → IngestionService（精确去重）
  → SQLFeedbackRepository（持久化）
```

- **归一化规则**（`normalization.py`，纯函数）：`raw_text` 折叠空白；`source`/`platform`/`customer_segment` 经映射表标准化（未识别 → `unknown`）；`rating` 仅接受 1~5 整数（否则 None）；`timestamp` 解析 ISO-8601。
- **精确去重**：以 `feedback_id` 为身份标识，同一 `feedback_id` 再次出现即跳过（含重复导入）。语义相似的判断留到聚类阶段。
- **数据模型**：`FeedbackItem` 采用固定字段（不再使用自由 metadata dict），与 CSV 摄取契约一一对应。
- **职责边界**：Repository 只做持久化与查询；去重编排在 `IngestionService`；归一化是纯函数，可独立测试。

## 9. 反馈理解层（Phase 3）

`app/services/analyzer.py`（`LLMFeedbackAnalyzer`）+ `app/prompts/analysis.py`（版本化 prompt）。

```
FeedbackItem → build_analysis_messages（prompt v1）→ LLM 单次调用 → 结构化输出校验 → FeedbackAnalysis
```

- 单次 LLM 调用 + 校验，非自主 Agent（pipeline-first）。
- 结构化输出：`FeedbackAnalysis` 受 Pydantic 约束（枚举 + 范围），analyzer 再兜底校验（空 summary → 报错），系统绝不静默接受非法输出。
- 系统字段（id / feedback_item_id / model / prompt_version / created_at）由 analyzer 组装，不信任 LLM 输出。
- 分类词表与 prompt 的一致性由测试守护（`test_prompt_lists_all_categories_and_issue_types`）。

## 10. 聚类层（Phase 4）

`app/services/clustering.py`（`EmbeddingClusteringService`）+ `app/services/embedding.py`（`EmbeddingProvider`）。

```
FeedbackItem + FeedbackAnalysis
  → Embedding（fastembed，真实）→ 余弦相似度 → 凝聚聚类（complete linkage，阈值）
  → outlier 分离 → LLM 命名（evidence-grounded）→ ProductProblem + Evidence
```

- embedding 与 LLM 分离为独立抽象（`EmbeddingProvider`），可单独替换。
- 凝聚聚类 complete linkage + 余弦阈值，precision-over-recall（宁可更细，再人工合并）。
- `other` 类别不参与聚类，但统计 count / percentage / samples。
- affected_segments 从 FeedbackItem.platform 元数据聚合（非 LLM 推断）。
- confidence 为确定性公式（基于证据数量），非 LLM 猜测。
- 结果经 `SQLProblemRepository` 持久化到 product_problems + evidence 两张表。

## 11. 优先级排序与机会生成（Phase 5）

`app/services/prioritisation.py`（`WeightedPrioritisationService`）+ `app/services/opportunity.py`（`LLMOpportunityGenerator`）。

- **优先级排序**：确定性加权打分（severity / frequency / breadth / business impact proxy），
  只排 confirmed（needs_review=False），candidate 不进入 ranking。
- **机会生成**：LLM 单次调用，evidence-grounded；系统字段由 generator 组装，不信任 LLM。
- business impact proxy = severity × frequency（占位，真实业务影响后续接入）。

