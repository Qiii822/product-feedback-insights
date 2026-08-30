# AI Product Feedback Agent — Phase 0：范围与架构

> **状态**：仅规划，尚未编写代码。
> **作者**：AI 产品经理（作品集项目）
> **本文目的**：让每一个假设显式化，明确我们**不**构建什么，并在写代码**之前**敲定架构。本文所有内容都可被质疑。

---

## 1. 产品假设

这些是产品赖以成立的信念。若其中任何一条有误，部分设计就需要调整。我们把它们写出来，使其可见。

| # | 假设 | 为什么重要 |
|---|------|-----------|
| A1 | 反馈以**短文本**形式到达（工单、应用商店评论、NPS 留言、bug 报告）。 | 决定摄取模型与输入 schema。 |
| A2 | 每条反馈**基本只围绕一个问题**。 | 若一条反馈混着 5 个问题，"一条反馈 → 一条分析"就会失效，聚类也会变乱。 |
| A3 | 反馈以**批处理**方式处理（数百到数千条），而非实时流。 | 可用批式聚类，无需流式/队列基础设施。 |
| A4 | 反馈**限定在单一产品或产品区域**（例如支付/收银台流程）。 | 领域越窄，聚类质量越高，演示越可信。 |
| A5 | 系统是**决策支持工具**，服务于人类 PM，而非自主决策者。 | 输出是*证据 + 建议*，绝不自动采取行动。 |
| A6 | **英语是 MVP 的主要语言**。 | 多语言聚类与评分会引入真实复杂度，我们暂缓。 |
| A7 | PM **审查并可覆盖**系统的聚类、严重程度与优先级。 | 要求数据模型把"人工编辑"当作一等公民，而非事后补充。 |

---

## 2. MVP 范围（基础阶段结束时"能用"的样子）

**范围内：**

1. 摄取一批反馈（来自文件与/或 API）。
2. 分析每条反馈 → 结构化的 `FeedbackAnalysis`（分类、严重程度、受影响人群、实体、摘要）。
3. 聚类分析结果 → 候选 `ProductProblem`，每个都有 `Evidence`（哪些条目支撑它）作支撑。
4. 校验聚类 → 每个问题一个 `confidence` 分数。
5. 问题排序 → 用透明的打分函数得到排序列表。
6. 为每个高优先级问题生成一个 `ProductOpportunity`（建议），并锚定其证据。
7. 持久化所有数据；通过一个小型 REST API 暴露。
8. 结构化日志 + 追踪*抽象*（不是平台）。
9. 一个评估框架，含一个小型、手写的数据集，可从 CLI 运行。

**基础的"完成"标准 =** 你能运行一条命令，喂入需求里的四条示例反馈，得到一份有证据支撑、已排序的问题列表和一条建议——全部持久化，且可针对评估集重复运行。

---

## 3. 非目标（显式声明，防止范围蔓延）

- ❌ 不做多 Agent 架构。
- ❌ 不做实时流 / webhook / 消息队列。
- ❌ 不做认证、角色、多租户。
- ❌ 不做生产级可观测性平台（我们建*接缝*，不建平台）。
- ❌ 不做 UI（那是 Phase 8）。
- ❌ 不做多语言、音频、视频或图片反馈。
- ❌ 不做自动行动（不自动建工单、不自动推送 Jira）。
- ❌ 不做模型微调。
- ❌ 不做在线数据连接器（Intercom、Zendesk、应用商店 API）。先用文件。

---

## 4. 用户工作流（PM 如何使用它）

1. **摄取** — PM 放入一个 CSV/JSON 反馈文件（或 POST），并给这批数据命名（如"收银台反馈 — 8 月"）。
2. **审查分析** — 系统返回每条反馈的结构化分析；PM 可快速浏览并纠正明显的分类错误。
3. **审查聚类** — 系统把条目归到问题下，每个问题带证据与置信度。PM 可合并/拆分/重命名聚类。
4. **排序** — 系统按可见公式给问题排序。PM 可重新调整各因素的权重。
5. **生成** — 对最靠前的问题，系统起草 `ProductOpportunity`（问题陈述 + 证据 + 受影响人群 + 严重程度 + 建议）。PM 编辑并导出。

注意：人在每个阶段都在环内。这是产品决策，不是技术局限。

---

## 5. Agent vs 确定性工作流分析（核心架构决策）

需求里的原则是：**确定性够用就用确定性，LLM 只在语义理解处使用，Agent 只在真正需要时使用。** 诚实地套用到我们的流水线：

| 阶段 | 机制（MVP） | 为什么 |
|------|------------|--------|
| **反馈理解** | 单次 **LLM 调用**，结构化输出 schema | 语义：分类意图、抽取实体（支付方式、平台）正是关键词规则会失效的地方。 |
| **问题聚类** | **确定性**：embedding → 相似度 → 聚类算法。**LLM 仅**用于之后给每个聚类*命名* | 聚类是数学问题。embedding 来自 LLM，但分组本身是确定性、可解释的。 |
| **问题校验** | **确定性** 一致性 + 证据数量检查；**可选 LLM 裁判**判断"这是否是同一个一致的问题" | 置信度应是可复现的公式，而非感觉。 |
| **优先级排序** | **确定性加权打分** | 排序是对严重程度、频率、人群重要度的算术。加 LLM 只会增加成本、降低可解释性。 |
| **产品机会** | 单次 **LLM 调用**，锚定问题 + 证据 | 建议的生成/综合是唯一明确需要生成的步骤。 |

**结论：这是流水线（pipeline），不是 Agent。**

- **流水线**是固定顺序的步骤，每步要么确定性、要么单次 LLM 调用。顺序已知，没有任何一步需要*决定下一步做什么*。
- **Agent** 是一个循环：LLM 选择工具、观察结果、重复直到达成目标。只有当系统必须*自适应*时才有用——例如动态拉取更多证据、追问澄清、尝试一种做法再改弦更张。

**我们的 MVP 不需要这种自适应。** 所以 Phase 1–5 我们构建流水线 + 一个 LLM 支撑的服务。`agents/` 目录会存在，但里面只是一个薄薄的 `FeedbackAnalysisAgent`——目前就是 LLM 服务的包装器。它是一个*接缝*，留空，这样若 Phase 6 真正需要 Agentic 行为，我们能原地生长，而不是推倒重写。

**以后什么会真正需要 Agent（Phase 6+）：**
- 校验需要*迭代搜索更多证据*来确认/推翻某个候选问题。
- 机会生成器需要*跨多个检索到的证据聚类做推理*再下笔。
- 自改进循环（生成 → 打分 → 修订）。

在以上任意一条成为真实需求之前，引入框架都是过早的。

---

## 6. 建议的架构

### 6.1 修订后的仓库布局

你建议的结构不错。我做了一些改动（已标注）——原因如下。

```
ai-feedback-agent/
├── pyproject.toml                # 依赖 + 工具配置（uv 或 poetry）
├── .env.example                  # 密钥/配置模板（绝不提交真实密钥）
├── .gitignore
├── README.md
├── Makefile                      # 或 justfile：常用命令（run / test / eval / ingest）
│
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI 入口 + 应用工厂
│   │   ├── api/                  # HTTP 层（路由、依赖、DTO）
│   │   │   ├── routes/
│   │   │   └── deps.py           # 依赖注入装配
│   │   ├── core/                 # 配置、日志、异常、追踪
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   ├── errors.py
│   │   │   └── tracing.py        # Tracer/Trace 抽象  <-- 新增
│   │   ├── models/               # ORM 模型（SQLAlchemy）
│   │   ├── schemas/              # Pydantic schema：API DTO + LLM 输出契约
│   │   ├── services/             # 业务逻辑（确定性 + LLM 支撑）
│   │   │   ├── analyzer.py       # FeedbackAnalyzer
│   │   │   ├── clustering.py     # ClusteringService
│   │   │   ├── prioritisation.py # PrioritisationService
│   │   │   ├── opportunity.py    # ProductOpportunityGenerator
│   │   │   └── llm.py            # LLMClient（provider 抽象）  <-- 放 services，不放 core
│   │   ├── agents/               # Agentic 接缝（目前薄包装器）
│   │   ├── tools/                # 工具接口（以后 agent 使用）
│   │   ├── repositories/         # 数据访问（FeedbackRepository, ...）
│   │   ├── prompts/              # 版本化 prompt 模板  <-- 版本化文件
│   │   └── evaluation/           # 评估框架（runner、grader、metrics）
│   │
│   ├── scripts/                  # CLI 入口：ingest、analyze、cluster、eval  <-- 新增
│   ├── alembic/                  # 数据库迁移  <-- 新增
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── evals/
│
├── data/                         # gitignored（或提交少量 fixture）
│   ├── raw/                      # 输入反馈文件
│   ├── processed/                # 中间产物
│   └── eval/                     # 手写评估用例 + 结果  <-- 结果放 eval/
│
├── docs/
│   ├── product/                  # PRD、用户工作流、决策
│   ├── architecture/             # ADR、图
│   └── decisions/                # ADR（或合并进 architecture/）
│
└── frontend/                     # Phase 8 前留空（保留目录，不添加内容）
```

**相比你的建议的改动与原因：**

1. **新增 `core/tracing.py`** — 可观测性是横切关注点，其抽象放在 `core`，与配置、日志相邻。
2. **把 LLM 客户端放进 `services/llm.py`** — LLM 是服务的*基础设施依赖*，不是应用管线。放 `services/` 意味着每个服务都能依赖它，而不必从 `core` 导入。
3. **新增 `scripts/`** — 流水线需要可运行的入口（ingest、analyze、cluster、eval）。没有它们，API 是唯一入口，作品集演示会很别扭。
4. **新增 `alembic/`** — schema 变更从第一天起就需要迁移，即便用 SQLite。
5. **`prompts/` 存*版本化*模板文件**（如 `analyze_v1.txt`），而非内联字符串——这让 prompt 版本成为可观测性可以指向的一等概念。
6. **`data/eval/results/`** — 评估输出与评估用例放在一起，不放在 `data/processed/`，使评估自包含、可复现。
7. **`frontend/` 留空** — 创造空间，但不提前绑定任何框架。

### 6.2 核心接口

这些是整个系统围绕的契约。它们让 LLM 供应商、存储、聚类算法*可替换*，而无需改动业务逻辑。

```python
# LLMClient — 唯一知道"用哪家供应商"的地方
class LLMClient(Protocol):
    def complete(self, messages, schema) -> Any          # 结构化补全
    def embed(self, texts: list[str]) -> list[list[float]]  # 聚类用 embedding

# FeedbackRepository — 唯一与存储打交道的地方
class FeedbackRepository(Protocol):
    def add(self, items: list[FeedbackItem]) -> None
    def get(self, id) -> FeedbackItem | None
    def list(self, filters) -> list[FeedbackItem]

# FeedbackAnalyzer — 反馈理解（LLM 支撑、结构化输出）
class FeedbackAnalyzer(Protocol):
    def analyze(self, item: FeedbackItem) -> FeedbackAnalysis

# ClusteringService — 问题聚类（确定性 + LLM 命名）
class ClusteringService(Protocol):
    def cluster(self, analyses: list[FeedbackAnalysis]) -> list[ProductProblem]

# PrioritisationService — 确定性排序
class PrioritisationService(Protocol):
    def prioritize(self, problems: list[ProductProblem]) -> list[ProductProblem]

# ProductOpportunityGenerator — LLM 支撑、锚定证据的生成
class ProductOpportunityGenerator(Protocol):
    def generate(self, problem: ProductProblem, evidence: list[Evidence]) -> ProductOpportunity

# Agent 工具（Phase 6 接缝）
class Tool(Protocol):
    name: str
    def run(self, input) -> Any

# 评估执行器
class EvaluationRunner(Protocol):
    def run_case(self, case: EvalCase) -> EvalResult
    def run_suite(self, suite) -> EvalReport

# Tracer（可观测性接缝）
class Tracer(Protocol):
    def start_trace(self, input) -> Trace
    def record_llm_call(self, trace, *, model, prompt_version, input, output, latency_ms, tokens) -> None
    def record_tool_call(self, trace, *, tool, input, output) -> None
    def end_trace(self, trace, *, final_result, error=None) -> None
```

上面的 `Protocol` 类型是契约的*形状*；实际代码中会是具体类（或 ABC），并配 `FakeLLM`、`InMemoryRepository`、`NullTracer` 用于测试。

---

## 7. 关键技术决策（含理由）

| 决策 | 选择 | 理由 |
|------|------|------|
| 语言/运行时 | **Python 3.11+** | ML/AI 生态最强；你的读者（AI PM）能读懂。 |
| Web 框架 | **FastAPI** | 异步、类型友好、原生契合 Pydantic；是 LLM 支撑 API 的自然选择。 |
| 数据校验 | **Pydantic v2** | 一个工具同时做 API DTO *和* LLM 输出契约。这是"绝不静默接受非法 LLM 输出"的落点。 |
| 数据库（MVP） | **SQLite**，经 SQLAlchemy 2.0 + Alembic | 零配置、文件即库、作品集极易检视。SQLAlchemy + Alembic 让后续切换 **Postgres** 成为配置级改动，而非重写。 |
| LLM 访问 | **直接 provider SDK 包在 `LLMClient` 后面**（不用框架） | 见 §8。一个接口、两个实现：真实 provider + 测试用 `FakeLLM`。 |
| 结构化输出 | **Pydantic schema + 校验 + 有界重试** | 模型返回 JSON，解析进 schema；非法 → 一次修复重试 → 硬错误（绝不静默默认）。 |
| 聚类 | **Embedding + 余弦相似度 + 凝聚聚类**（可调阈值） | 确定性、可解释、无需猜测 `k`。若离群点（"杂项"条目）成为问题，HDBSCAN 是后续替代。 |
| 优先级排序 | **确定性加权打分**，权重在配置里 | 排序是算术。LLM 在上游提供*输入*（严重程度、人群）；排序本身透明、可复现。 |
| 置信度 | **确定性公式**（证据数量、embedding 内聚、一致度） | 一个能解释的置信度数字，胜过你无法解释的 LLM"0.84"。 |
| 配置 | **pydantic-settings** 读 env + `.env` | 密钥（API key）不进 git；provider/模型经环境变量切换。 |
| 日志 | **`structlog`**（JSON、结构化） | 直接喂给追踪故事；现在采用成本低。 |
| 测试 | **pytest**（+ `pytest-asyncio`） | 单元测试绝不碰真实 LLM（用 `FakeLLM`）；集成测试碰 SQLite。 |
| 依赖管理 | **`uv`**（或 Poetry） | 快、可复现；二选一，保持一致即可。 |

### 7.1 结构化输出 & "绝不静默接受非法 LLM 输出"

不变量：**LLM 返回 JSON，我们解析进 Pydantic schema，若解析失败，做一次修复尝试，然后大声失败。** 绝不回退到"尽力而为"的解析而悄悄丢弃字段。

数据模型草图（字段级、高层——实现是 Phase 2）：

- **`FeedbackItem`** — `id`、`raw_text`、`source`、`external_id`、`created_at`、`metadata`（平台、设备、地区、人群）。
- **`FeedbackAnalysis`** — `id`、`feedback_item_id`、`summary`、`category`、`severity`、`affected_segment`、`entities`、`is_actionable`、`confidence`、`model`、`prompt_version`、`created_at`。
- **`ProductProblem`** — `id`、`title`、`description`、`category`、`severity`、`affected_segments`、`confidence`、`status`（`candidate` → `validated` → `prioritized`）、`evidence_count`、`cluster_centroid`。
- **`Evidence`** — `id`、`product_problem_id`、`feedback_item_id`、`analysis_id`、`relevance_score`。
- **`ProductOpportunity`** — `id`、`product_problem_id`、`title`、`summary`、`recommendation`、`expected_impact`、`confidence`、`evidence_refs`、`generated_at`。

### 7.2 可观测性接缝（以后追踪，现在不建平台）

每个阶段接受可选的 `Tracer`。默认实现是 `InMemoryTracer`（把 trace 存进 DB 或日志）。我们记录的字段——匹配你的需求——是：

`run_id`、`input`、`model`、`prompt_version`、`tool_calls[]`、`tool_inputs[]`、`tool_outputs[]`、`model_output`、`latency_ms`、`token_usage`（若 provider 报告）、`errors`、`final_result`。

以后你把 `InMemoryTracer` 换成 LangSmith / OpenTelemetry / W&B，**无需改动服务代码**——这正是接缝的意义。

---

## 8. 框架分析（为什么现在不用）

你要求我在采用任何框架之前论证。这是诚实的分析。

| 框架 | 解决什么 | 带来的复杂度 | 我们 MVP 需要吗？ |
|------|---------|-------------|------------------|
| **LangChain / LlamaIndex** | 链式调用、检索器、prompt 模板、RAG | 一大层抽象；隐藏 LLM 调用；更难调试；API 变化快 | **不需要。** 我们流水线就 5 步。普通 Python 函数 + 一个 `LLMClient` 接口更清晰、更可教。 |
| **LangGraph** | 有状态、基于图的*Agent*编排 | 概念负担（节点/边/状态）、调试开销 | **暂不需要。** 我们还没有 Agent 循环要编排。Phase 6 再议。 |
| **CrewAI / AutoGen** | 多 Agent 协作、角色扮演 Agent | 重；有主见；为多 Agent 系统而建，而我们明确不需要 | **不需要。** 多 Agent 是非目标。 |
| **MCP（模型上下文协议）** | 标准化*模型如何调用外部工具* | 新协议面、client/server 管线 | **暂不需要。** 我们没有外部工具要调。以后若 Agent 需要查询在线数据源，会有用。 |
| **LiteLLM** | 一个 API 调多家 provider | 多一个依赖 + 间接层 | **可选。** 单个 `LLMClient` 接口 + 两个实现，对我们单 provider 的 MVP 已够用。需要 3+ provider 时再加。 |

**建议：** 用普通 Python 编排（函数 + Pydantic + FastAPI），配手写的 `LLMClient` 抽象。这是满足需求的最简架构，也正是需求里的原则所要求的。

---

## 9. 你需要做的关键产品决策

这些由你决定。每个块里给出我的建议，但选择权在你。

### D1 — LLM provider
- **选项**：(a) Anthropic Claude，(b) OpenAI GPT，(c) 接口后面两者都接，(d) 暂时仅 mock。
- **权衡**：Claude 对结构化输出/工具使用支持极好，且对这类任务有很强的叙事；OpenAI 类似，工具链不同；"两者"加倍表面积；"仅 mock"延迟成本，但无法演示真实质量。
- **建议**：**(a) Anthropic Claude**（如 `claude-sonnet-5` 做分析、`claude-haiku-4-5` 做廉价高量）——*包在* `LLMClient` 接口后面，所以替换是琐事。
- **理由**：它是结构化抽取的最强默认，且接口已让它可替换——所以这不是锁死决策。

### D2 — 反馈如何进入系统（MVP）
- **选项**：(a) CSV/JSON 文件上传，(b) REST API 摄取端点，(c) 两者。
- **权衡**：文件最简单，匹配批式聚类；API 更"产品化"但增加 DTO/校验表面积；两者工作更多。
- **建议**：**(a) 先文件**，repository 设计成让 API 端点是后来的薄层。
- **理由**：你能用一条命令从文件演示完整流水线；API 可以增长而无需改动摄取逻辑。

### D3 — 领域范围
- **选项**：(a) 单一具体领域（支付/收银台示例），(b) 通用多领域，(c) 领域作为每数据集配置。
- **权衡**：单一领域 → 紧凑、可信的聚类和干净演示；通用 → 更难展示质量；可配置 → 两全但前期设计更多。
- **建议**：**(a) 单一具体领域**（收银台/支付），`metadata` 保持开放以便以后加第二个领域。
- **理由**：聚类质量与评估真值在一个领域内要容易得多，这正是作品集演示需要的可信度。

### D4 — 数据库
- **选项**：(a) SQLite（MVP）→ 以后 Postgres，(b) 现在就 Postgres。
- **权衡**：SQLite 零配置、可移植；Postgres 更贴近生产但需要跑服务/Docker。
- **建议**：**(a) 现在 SQLite**，部署时再 Postgres。
- **理由**：SQLAlchemy + Alembic 让后续切换很便宜，而"免安装随处可跑"对作品集评审者是超能力。

### D5 — 部署 / 目标环境
- **选项**：(a) 仅本地（在你笔记本跑），(b) Docker 容器，(c) 云端托管。
- **权衡**：本地最快搭建与演示；Docker 让评审者可复现；云端花钱且需要你解释的基础设施。
- **建议**：**(a) 现在仅本地**，只有在需要评审者自己跑时才加 Dockerfile。
- **理由**：学习与作品集价值在架构与评估，不在托管。

### D6 — 严重程度与置信度语义
- **选项**：(a) 严重程度是固定序数刻度（低/中/高/严重），(b) 连续 0–1，(c) 两者（序数标签 + 连续分数）。
- **权衡**：序数对人友好、可评分；连续更细但更难解释与评估；两者最丰富但 schema 更多。
- **建议**：**(c) 两者** — 一个序数 `severity` 标签 *加上* 一个连续 `confidence` 分数。它们回答不同的问题（"多糟" vs "多确定"）。
- **理由**：你的示例已经隐含了这点：`Severity: High` 和 `Confidence: 0.84` 是两个不同的轴。

---

## 10. 初始评估策略（从第一天开始建）

评估回答一个问题：**系统是否在*变得越来越正确*？** 它与产品*并行*构建，而非事后。

### 10.1 评估用例形状

每个手写用例恰好包含你的需求所要求的内容：

```yaml
- id: "payments-apple-pay"
  input_feedback: "Couldn't pay with Apple Pay."
  expected:
    category: "payment_failure"
    key_evidence: ["apple pay", "payment", "checkout"]
    severity: "high"
    outcome: "investigate the apple pay checkout flow"
```

### 10.2 Grader — 确定性优先，LLM 仅在必要时

| 属性 | Grader | 为什么 |
|------|--------|--------|
| `category` | 精确/其一匹配 → 精确率/召回率/F1 | 确定性。 |
| `key_evidence` | 包含（期望证据是否出现在该聚类条目中？） | 确定性。 |
| `severity` | 精确匹配，或序数刻度上 ±1 | 确定性。 |
| `outcome` | **LLM-as-a-judge** 判断*语义等价*（或模糊/embedding 相似度） | 自由文本不能用字符串匹配评分。清晰标注为唯一的 LLM 裁判场景。 |

### 10.3 Runner 与指标

- `EvalRunner` 把用例跑过相关阶段，存 `EvalResult`（期望 vs 实际、评分），聚合成 `EvalReport`。
- 计算的指标：分类 **准确率**、分类 **精确率/召回率/F1**、证据 **归属精确率/召回率**、严重程度 **准确率**（及混淆矩阵）、每次运行 **延迟** 与 **成本**。
- 结果带时间戳与 run ID 写入 `data/eval/results/`，让你能对比"改 prompt 前后"。

### 10.4 规则

1. **确定性 grader 优先。** LLM-as-a-judge 只用于自由文本语义等价，且仅在模糊/embedding 指标不够好时。
2. **评估用例版本化且小**（先 10–20 条手写）。发现失败时再增长。
3. **失败的评估是发现，不是评估的失败。** 循环是：跑 → 看失败 → 修 prompt/逻辑 → 重跑。

---

## 11. 产品指标（仅占位——不编造数字）

这些是*定义*，不是主张。现在为它们埋点，等有真实数据后填值。

| 指标 | 定义 | 何时填充 |
|------|------|---------|
| 反馈分类准确率 | 分类与人工标签一致的条目占比 | 评估集存在后 |
| 聚类质量 | silhouette / 与人工聚类的 adjusted Rand | 有人工聚类数据后 |
| 问题识别精确率 | 浮出的问题里真实问题的占比 | PM 审查后 |
| 证据归属准确率 | 正确关联到问题的条目占比 | 审查后 |
| 严重程度分类准确率 | 严重程度与人工判断一致的占比 | 评估集后 |
| 幻觉率 | 输出中含有输入中不存在证据的占比 | 需要检测机制（如证据引用检查） |
| 任务完成率 | 无错误完成的运行占比 | 来自追踪 |
| 延迟 | 端到端运行时间 p50/p95 | 来自追踪 |
| 每 100 条反馈成本 | tokens × 价格 / 100 条 | 来自追踪 + provider 定价 |

**我们现在记录每个指标所需的*字段*（经追踪），以后才计算指标。** 我们绝不编造一个数字去填幻灯片。

---

## 12. 建议的 Phase 1 计划

**Phase 1 目标：** 一个可编译、可运行、结构良好的骨架，尚**无业务逻辑**——其余部分赖以生长的地基。

1. 初始化仓库（上面的目录布局、`pyproject.toml`、`.gitignore`、`.env.example`、README 骨架）。
2. 搭起配置管理（`core/config.py`，pydantic-settings）+ 日志设置。
3. 为五个核心数据类型建 Pydantic schema（仅契约，尚未接存储）。
4. 定义核心接口（§6.2）为 ABC/Protocol，配 `Fake`/`InMemory`/`Null` 实现。
5. 建 SQLAlchemy 模型 + Alembic 设置（schema 迁移）。
6. 脚手架 FastAPI 应用 + 一个健康检查端点。
7. 搭 `pytest` + 首批单元测试（配置加载、schema 校验往返）。
8. 桩追踪抽象。
9. 写 README + 指向本文的简短架构文档。

**Phase 1 验收标准：**
- `pytest` 可跑且通过（仅单元测试）。
- API 可启动，`/health` 返回 200。
- `alembic upgrade head` 建出 SQLite schema。
- 尚无 LLM 调用、无聚类、无评估用例——只有骨架。

**Phase 1 之后我会汇报**（按你的流程）：建了什么、为什么、架构决策、该人工检查什么、该跑什么测试、什么可能失败——然后停下等你的确认。

---

## 13. 给你的开放问题（Phase 1 之前）

1. 上面的 D1–D6 决策——你选哪些？（至少 D1、D2、D3 能解锁构建。）
2. 你选择的 provider 的 API key 准备好了吗，还是我们先 `FakeLLM`，等你准备好再接真实 provider？
3. 你需求里的收银台/支付示例就是 MVP 的规范领域吗，还是你心里有别的？
4. `uv` 还是 Poetry（或者都不用——普通 `pip` + `requirements.txt`），有偏好吗？
