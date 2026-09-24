# Product Feedback Insights

将大量非结构化的客户反馈，转化为**有证据支撑的产品洞察**的产品分析工具。

这是一个面向 AI 产品经理（AI PM）的作品集项目。它不仅是"能跑通"，更重要的是展示一套**清晰、可替换、可评估**的 AI 系统架构，以及背后的产品与技术决策。

> 当前状态：**Product Feedback Intelligence** —— 在"摄取 → 分析 → 聚类 → 排序 → 建议"基础上，新增 **Issue Intelligence（趋势/情绪/占比/版本）、可解释排序（因子分解）、诊断（FACT/HYPOTHESIS/UNKNOWN）、执行摘要**。已接入真实 DeepSeek 并端到端跑通，提供浏览器 dashboard 与可观测性（run_id / 耗时 / token），含评估框架（分类 / 聚类 / 排序 / 置信度校准）与 101 个单元测试。**运行需要真实 `DEEPSEEK_API_KEY`（未配置即报错，不再回退 mock）。**

---

## 核心原则

1. **确定性优先**：能用确定性软件解决的问题，不用 LLM。
2. **LLM 只在语义理解处使用**：分类、抽取、聚类命名、生成建议等。
3. **Pipeline 优先，而非 Agent**：当前 MVP 是一条固定流水线，不是自主 Agent。只有当确有必要（动态工具选择 / 迭代推理）时才引入 Agentic 行为。
4. **永远可替换**：LLM 供应商、存储、聚类算法、追踪后端，都通过接口隔离，可独立替换。
5. **永不静默接受非法输出**：LLM 输出必须解析为结构化 schema，非法则失败。

---

## 架构概览

```
原始反馈 → 反馈理解 → 问题聚类 → Issue Intelligence → 优先级排序 → 诊断 → 产品机会 → 执行摘要
```

| 阶段 | 机制（当前） |
|------|------------------|
| 反馈理解 | 单次 LLM 调用，结构化输出 |
| 问题聚类 | 确定性（embedding + category-aware） |
| Issue Intelligence | 确定性聚合（趋势 / 情绪 / 占比 / 版本） |
| 优先级排序 | 确定性加权打分（可分解：严重度 / 量 / 增长 / 广度） |
| 诊断 | FACT 确定性 + HYPOTHESIS / UNKNOWN 单次 LLM（evidence-grounded） |
| 产品机会 | 单次 LLM 调用，基于证据生成 |
| 执行摘要 | 确定性聚合（负评率 / 情绪变化 / 新兴问题） |

详细架构与决策见 [`docs/architecture/architecture.md`](docs/architecture/architecture.md) 与 [`docs/decisions/decision-log.md`](docs/decisions/decision-log.md)。

---

## 目录结构

```
product-feedback-insights/
├── app/
│   ├── api/            # HTTP 层（路由）
│   ├── core/           # 配置、日志、追踪
│   ├── db/             # SQLAlchemy engine / session / Base
│   ├── models/         # ORM 模型
│   ├── schemas/        # Pydantic 数据契约（schema）
│   ├── services/       # 业务接口 + LLM 客户端实现
│   ├── repositories/   # 存储实现
│   └── static/         # 浏览器 UI（HTML / JS / CSS）
├── alembic/            # 数据库迁移
├── tests/              # 单元测试
├── data/               # raw / processed / eval（数据文件，gitignore）
└── docs/               # architecture / decisions 文档
```

---

## 快速开始

本项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 依赖与虚拟环境（自动使用 Python 3.12）。

```bash
# 1. 安装依赖
uv sync

# 2. 配置 LLM（必需：未配置则运行时报错，不会静默回退 mock）
cp .env.example .env
# 编辑 .env，填入：
#   DEEPSEEK_API_KEY=sk-你的key
#   DEEPSEEK_MODEL=deepseek-chat

# 3. 初始化数据库
uv run alembic upgrade head

# 4. 跑完整 pipeline（摄取 → 分析 → 聚类 → 排序 → 建议）
uv run python -m scripts.ingest data/raw/sample_feedback.csv
uv run python -m scripts.cluster
uv run python -m scripts.prioritize

# 5. 运行评估（真实 DeepSeek 分类评估 / 全量 baseline）
uv run python -m scripts.evaluate_deepseek
uv run python -m scripts.evaluate

# 6. 运行单元测试
uv run pytest
```

> `.env` 已被 `.gitignore` 忽略，API key 不会进入版本控制。

## 浏览器 UI

启动服务后，在浏览器打开 **http://127.0.0.1:8000** 即可看到 dashboard：

```bash
uv run uvicorn app.main:app --reload
# 打开 http://127.0.0.1:8000
```

UI 支持：上传 CSV/JSON → 摄取（或点「载入示例数据」一键灌入 48 条模拟反馈 `data/raw/mock_feedback.csv`）→ 运行完整分析 → 查看**执行摘要**（负评率/情绪变化/新兴问题）、Top 机会建议、按优先级排序的产品问题（趋势/情绪/占比/版本/排序分解/诊断/证据），并可点击摘要中的 issue 下钻到完整 Issue Intelligence。另可「运行分类评估」查看 accuracy / F1 / per-category / reliability curve / needs_review 召回。

---

## 五个核心数据契约（`app/schemas/`）

| Schema | 作用 |
|--------|------|
| `FeedbackItem` | 一条原始客户反馈（固定字段：feedback_id / raw_text / source / platform / app_version / customer_segment / rating / timestamp） |
| `FeedbackAnalysis` | 反馈理解阶段的输出（primary_category / issue_type / severity / confidence / needs_review） |
| `ProductProblem` | 聚类得到的候选产品问题 |
| `Evidence` | "某条反馈支撑某问题"的关联，保证可追溯 |
| `Diagnosis` | 结构化诊断（facts / hypotheses / unknowns），区分事实与假设 |
| `ProductOpportunity` | 最终建议，强制引用证据（抗幻觉） |

## 核心接口（`app/services/interfaces.py`）

| 接口 | 替换点 |
|------|--------|
| `LLMClient` | LLM 供应商（DeepSeek） |
| `EmbeddingProvider` | Embedding（当前 fastembed / Fake） |
| `FeedbackRepository` | 存储（InMemory / SQL） |
| `FeedbackAnalyzer` | 反馈理解（LLMFeedbackAnalyzer） |
| `ClusteringService` | 聚类算法（EmbeddingClusteringService） |
| `PrioritisationService` | 排序打分（WeightedPrioritisationService） |
| `ProductOpportunityGenerator` | 建议生成（LLMOpportunityGenerator） |
| `EvaluationRunner` | 评估执行（Phase 7） |

---

## 开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 范围与架构澄清 | ✅ 完成 |
| Phase 1 | 仓库骨架 / 配置 / schema / 接口 / 测试 | ✅ 完成 |
| Phase 2 | 数据模型 + 摄取 | ✅ 完成 |
| Phase 3 | 单条反馈分析 | ✅ 完成 |
| Phase 4 | 聚类 | ✅ 完成 |
| Phase 5 | 优先级排序 + 机会生成 | ✅ 完成 |
| Phase 6 | 仅在确有必要处引入 Agentic 行为 | ⏸️ 评估显示暂无必要 |
| Phase 7 | 评估套件 | ✅ 完成 |
| Phase 8 | UI | ✅ 完成 |
| Phase 9 | 可靠性 / 可观测性 / UX | ✅ 完成 |
