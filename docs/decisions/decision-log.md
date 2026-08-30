# 决策日志（Decision Log）

> 记录 Phase 1 的关键技术决策。每个决策按「决策 / 备选方案 / 权衡 / 为什么」记录。
> 约定：Python 变量名、类名、函数名、API 端点、数据库表/列名、包名、Git 提交信息保持英文；
> 文档、注释、决策日志使用中文。

---

## ADR-001：MVP 采用 Pipeline-first，而非自主 Agent

- **决策**：当前 MVP 用固定流水线（确定性步骤 + 单次 LLM 调用），不引入自主 Agent。
- **备选方案**：Agentic loop（LLM 自主选择工具、迭代推理）；多 Agent 框架（LangGraph / CrewAI / AutoGen）。
- **权衡**：Pipeline 可解释、可逐段测试、确定性高；Agent 灵活但难评估、难调试、当前无明确需求。
- **为什么**：MVP 五个阶段都不需要动态决策。先把确定性 Pipeline 实现并完成 Evaluation，再根据实际问题判断哪里真正需要 Agentic 行为。这是阶段性决策，不是永久限制。

## ADR-002：技术栈 Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0

- **决策**：后端用 Python 3.12 + FastAPI；数据校验用 Pydantic v2；持久化用 SQLAlchemy 2.0 + Alembic。
- **备选方案**：Node/TypeScript；Django；纯手写 SQL。
- **权衡**：FastAPI 异步、类型友好、Pydantic 原生契合"结构化输出"；SQLAlchemy + Alembic 让 SQLite → Postgres 切换成为配置级改动。
- **为什么**：这是 AI 后端的主流组合，对 AI PM 评审者最易理解；Pydantic 是"永不静默接受非法 LLM 输出"这一原则的落点。

## ADR-003：用 uv 管理 Python 依赖与虚拟环境

- **决策**：使用 `uv` 统一管理依赖、锁文件与 Python 版本。
- **备选方案**：Poetry；pip + venv + requirements.txt。
- **权衡**：uv 快、内置 Python 版本管理（本机系统 Python 3.9 过旧，uv 直接拉取 3.12）、单一 `pyproject.toml`；Poetry 类似但较慢。
- **为什么**：一个工具解决"依赖 + 虚拟环境 + Python 版本"三件事，降低作品集评审者的上手成本。

## ADR-004：数据库 SQLite（Phase 1）→ Postgres（部署时）

- **决策**：开发阶段用 SQLite（零配置、文件即库），通过 SQLAlchemy + Alembic 保留切换能力。
- **备选方案**：一开始就用 Postgres（需 Docker/服务）。
- **权衡**：SQLite 可移植、免安装、便于评审者一键复现；Postgres 更接近生产但不增加当前价值。
- **为什么**：`DATABASE_URL` 改一个连接串即可切换，架构已为此埋好 seam，无需提前承担运维复杂度。

## ADR-005：接口用 abc.ABC（抽象基类），而非 typing.Protocol

- **决策**：核心接口（`LLMClient`、`FeedbackRepository` 等）用 `abc.ABC` + `@abstractmethod`。
- **备选方案**：`typing.Protocol`（结构化/鸭子类型，无需显式继承）。
- **权衡**：Protocol 更灵活；ABC 让"这是接口"更显式，且实例化未实现接口的类会立即抛 `TypeError`。
- **为什么**：这是教学向的架构示范，明确、可验证的契约（测试能断言"接口不可实例化"）比灵活性更重要。

## ADR-006：日志用标准库 logging，而非 structlog

- **决策**：Phase 1 用 Python 标准库 `logging`，配置一个简单 formatter。
- **备选方案**：structlog / loguru（结构化 JSON 日志）。
- **权衡**：structlog 为"结构化日志 → tracing"预留更好基础，但当前无结构化日志需求。
- **为什么**：零依赖、够用。当 tracing 真正需要结构化日志时（Phase 6+），可低成本迁移。

## ADR-007：目录布局采用扁平 `app/`，而非 `backend/app/`

- **决策**：应用包放在仓库根目录 `app/`，不用 `backend/` 包裹层。
- **备选方案**：`backend/app/`（为未来 `frontend/` 预留 monorepo 结构）。
- **权衡**：扁平布局是 FastAPI 生态的惯例，少一层嵌套、导入更简洁；`backend/` 包裹层在 `frontend/` 真正存在时（Phase 8）才有意义，届时一次性迁移是低风险的机械改动。
- **为什么**：遵循"不为未来而加结构"的原则——`frontend/` 现在还不存在。

## ADR-008：ORM 模型加 `Model` 后缀，列名 `metadata_json`

- **决策**：ORM 模型命名为 `FeedbackItemModel`（区别于 Pydantic schema `FeedbackItem`）；`metadata` 字段在数据库列名为 `metadata_json`。
- **备选方案**：ORM 与 schema 同名；列名直接叫 `metadata`。
- **权衡**：加后缀避免 ORM 与 schema 混淆；`metadata` 与 SQLAlchemy 的 `Base.metadata` 冲突，必须改名。
- **为什么**：清晰区分"数据契约"与"数据库表"两个层次，并规避框架保留字。

## ADR-009：LLM 接入采用 mock-first（FakeLLM / NullLLM）

- **决策**：当前只提供 `FakeLLM`（确定性假输出）与 `NullLLM`（调用即报错），不接真实 API。
- **备选方案**：立即接入 Anthropic/OpenAI。
- **权衡**：mock 不花钱、可复现、离线可测，用于先验证架构与结构化输出契约；真实 provider 后续作为新的 `LLMClient` 实现加入。
- **为什么**：先证明"替换 seam 和契约"是成立的，再花 API 成本——这也让整个 Phase 1~5 可在无网络/无密钥环境下完成。

---

## ADR-010：FeedbackItem 采用固定字段，不用自由 metadata dict

- **决策**：`FeedbackItem` 固定 `feedback_id / raw_text / source / platform / app_version / customer_segment / rating / timestamp` 字段，移除自由 `metadata` dict。
- **备选方案**：保留自由 dict，按需往里塞字段。
- **权衡**：固定字段强类型、可校验、便于按字段聚类/过滤；自由 dict 灵活但无法约束、易滋生脏数据。
- **为什么**：这些字段是已知的、高价值的分析维度（平台、分群、评分等），值得作为一等公民建模；未来确有新字段时再加列（迁移）即可。

## ADR-011：精确去重以 feedback_id 为身份，语义去重留给聚类

- **决策**：摄取层仅做精确去重——同一 `feedback_id` 再次出现即跳过（含重复导入/同批重复）；不做文本语义去重。
- **备选方案**：按归一化后的 `raw_text` 去重（会合并不同来源的相同文本）。
- **权衡**：以 `feedback_id` 去重无歧义、不会误合并"不同客户写出的相同文本"；按文本去重可能低估证据数量（两个真实客户写了同一句话被当成一条）。
- **为什么**：语义相似（含"不同客户写的相似/相同反馈"）本质是聚类问题，交给 Phase 4 处理，摄取层保持简单、可预测。

## ADR-012：LLM provider 未来选 DeepSeek，不围绕 Anthropic 设计

- **决策**：配置只保留 `deepseek_api_key`（未来通过 `DEEPSEEK_API_KEY` 环境变量注入），移除 `anthropic_api_key` / `openai_api_key`；任何 API key 不得进入 git。
- **备选方案**：同时预留多家 provider 的 key 字段。
- **权衡**：单一 provider 字段最简洁、无冗余；未来若需多 provider，再加字段即可。
- **为什么**：项目明确不使用 Anthropic；当前 mock-first 阶段本就无真实调用，等接入 DeepSeek 时通过环境变量注入密钥，符合"不为未来而加结构"。

---

## ADR-013：区分"字段缺失（None）"与"无法识别（unknown）"

- **决策**：枚举字段（source / platform / customer_segment）未提供 → `None`；提供了但无法映射 → `"unknown"`。数据库这三列改为 nullable（不再 NOT NULL + 默认 "unknown"）。
- **备选方案**：两者统一归为 `"unknown"`（Phase 2 初版做法）。
- **权衡**：区分能保留"数据缺失"这一信号（缺失可能是数据管道问题，`unknown` 是词典覆盖不全）；统一更简单但丢失信息。
- **为什么**：缺失与无法识别在分析上含义不同，且直接影响后续按平台/人群切片的准确性。

## ADR-014：rating 无效 → 记录警告，不丢弃整条反馈

- **决策**：rating 缺失 → `None`（无警告）；提供了但解析失败/越界 → `None` + 明确的 ingestion warning，**不丢弃整条反馈**。
- **备选方案**：静默转 None；或把整条反馈判为 invalid 丢弃。
- **权衡**：静默会丢失"数据质量"信号；丢弃会损失仍有价值的 `raw_text` 证据。
- **为什么**：rating 是辅助字段，不应因它丢掉反馈主体；但无效 rating 值得被记录，以持续改进数据质量。

---

## ADR-015：产品问题分类法（Taxonomy）最终定稿

- **决策**：`primary_category` 采用 **11 个 flat 类**（`payment_declined` / `payment_failed` / `payment_timeout` / `payment_method_missing` / `payment_method_not_working` / `checkout_stuck` / `checkout_crash` / `checkout_performance` / `duplicate_charge` / `incorrect_charge` / `other`），并引入独立的 `issue_type` 维度。详见 `docs/product/category-taxonomy.md`。
- **备选方案**：14 个层级 leaf；或含 authentication / refund 的更大分类法。
- **权衡**：flat 11 类更易让 LLM 稳定分类（更少模糊边界），但覆盖度略低；层级更丰富但增加分类不确定性与评估成本。
- **为什么**：MVP 目标是 taxonomy **一致性（consistency）**而非**完备性（completeness）**；粒度暂不锁死，评估出现稳定且有产品意义的新 failure mode 时再增类。

**关键子决策：**

1. **checkout_crash 严格限定 checkout/payment 上下文**——"点击 Pay 崩溃"→ `checkout_crash`；"打开 Settings 崩溃"/"一直崩溃"（无 checkout 上下文）→ `other`。不设泛化 crash 类，避免领域扩张到 General App Reliability。
2. **frozen 与 stuck 合并**为 `checkout_stuck`（覆盖冻结 / 卡住 / 无限加载 / spinner 不停 / 无法推进）；评估显示是稳定且有产品意义的不同 failure mode 时再拆。
3. **refund 不作 primary category**，引入独立 `issue_type` 维度（`problem` / `request` / `question` / `feedback`）区分："我要退款"→ `request`；"退款没到账"→ `problem`。退款反馈 `primary_category = other`。
4. **单标签**：每条反馈只有一个 `primary_category`；多问题/难取舍时用低 `confidence` + `needs_review = true` 表达不确定性，不做 multi-label。
5. **`other` 是正式评估类别**：评估单独统计 `other` precision / recall / overall other rate；既不让 `other` 成为逃避默认，也不强迫 out-of-domain 反馈挤进具体类。
6. **分析维度独立**：`primary_category` 不承载 severity / issue_type / root cause / priority；它们是独立维度：Feedback → primary_category / issue_type / severity / confidence / evidence / needs_review。

**补充（3DS 归属与维度独立性）：**

- **3DS / authentication 暂归 `payment_failed`，不新增独立类**，但有严格边界：**仅当 3DS / 支付认证失败明确导致支付无法完成时**归 `payment_failed`；若核心问题是收银台卡住 / 加载缓慢 / 性能，按实际症状归 `checkout_stuck` / `checkout_performance`，不能仅因出现"3DS"就归 `payment_failed`。未来 Evaluation 证明 3DS 反馈规模足够、分类稳定、且具独立产品决策价值时，再考虑拆出独立 category。
- **维度独立性（明确示例）**：`issue_type` 不决定 `primary_category`。"I want Apple Pay to be supported." → `primary_category = payment_method_missing`、`issue_type = request`；"Can I pay with Apple Pay?" → `primary_category = payment_method_missing`、`issue_type = question`。不要因 `issue_type` 是 request / question 就自动归 `other`。

---

## ADR-016：Phase 4 聚类设计（embedding / 算法 / 阈值 / 持久化）

- **决策**：embedding 用 `fastembed`（本地 ONNX，`BAAI/bge-small-en-v1.5`，无 API key），并拆为独立 `EmbeddingProvider` 抽象（与 LLMClient 分离）。聚类用**凝聚聚类 + complete linkage + 余弦相似度阈值 0.75**；单成员簇视为 outlier；`other` 不参与聚类但统计；结果持久化到 product_problems + evidence 表。
- **备选方案**：sentence-transformers（本地 PyTorch，重）；Embedding API（需 key）；sklearn 聚类（多依赖）；connected-components 聚类（会链式过度合并）。
- **权衡**：fastembed 轻量、离线、无 key，但模型选择较少；complete linkage 最保守（precision-over-recall），但可能偏细；手写凝聚聚类零依赖但 O(n³)（≤1000 条可接受）。
- **为什么**：embedding 与 LLM 解耦便于单独替换；complete linkage + 阈值直接落地"宁可更细，再人工合并"；`other` 单独统计保留"out-of-domain / 覆盖不足"信号。

**关键子决策：**

1. **相似度阈值 0.75**（可配置 `clustering_threshold`）：余弦相似度 ≥ 0.75 才视为同一问题。
2. **confidence = min(0.95, 0.5 + 0.1 × 证据数)**：确定性公式，占位（Phase 5+ 可引入内聚/一致度）。
3. **affected_segments 从 FeedbackItem.platform 元数据聚合**（按频次），非 LLM 推断。
4. **outlier = 单成员簇**（从未与其他反馈达到阈值的条目）。
5. **`other` 排除但统计**：count / percentage / representative samples。

---

## ADR-017：Phase 4 review 调整（threshold / confidence / cohesion / singleton）

- **决策**：① 阈值 0.75 只是 **initial heuristic**，不是 validated production threshold，Phase 7 用标注评估集校准；② 删除 `min(0.95, 0.5+0.1·evidence_count)` 这个 confidence 公式——confidence 改为 **provisional 占位（0.5）**，不用于产品决策；③ 新增 **cohesion_score**（簇内平均到质心相似度），与 confidence 分离；④ **单成员簇不再是 outlier，而是 candidate problem（needs_review=True）**，不静默隐藏高严重度/高影响单条反馈。
- **备选方案**：把 evidence_count 当 confidence；单成员自动丢弃。
- **权衡**：evidence_count 不能代表可信度（两条噪声也能凑一簇）；丢弃单条会漏掉有价值的孤例。
- **为什么**：confidence 需 Phase 7 的校准（semantic coherence / similarity to centroid / category consistency / evidence quality / cluster size）；cohesion 是确定性可解释指标；单条反馈应保留供人工判断。

**关键点：**

1. **已知失败案例**："Payment page froze."（checkout_stuck）被 embedding-only 聚类并入 payment_failed 簇。已记录到 `data/eval/known_failures.md`，Phase 7 引入 category-aware 聚类（semantic similarity + primary_category compatibility）并加入评估集。
2. **affected_segments 仅 platform**，不新增 customer_segment（除非 ingestion 数据真实提供）。

---

## ADR-018：Phase 5 优先级排序与机会生成

- **决策**：优先级用**确定性加权打分**：`score = w_severity·severity_norm + w_frequency·frequency_norm + w_breadth·breadth_norm + w_impact·impact_norm`（各项归一化到 0~1，权重可配置）。只排 confirmed（needs_review=False），candidate 不进入 ranking。机会生成用 LLM 单次调用，evidence-grounded，系统字段（id / product_problem_id / evidence_refs / confidence）由 generator 组装。
- **备选方案**：LLM 直接打分（不可解释）；RICE 等现成框架。
- **权衡**：确定性加权透明、可复现、可调权重；LLM 打分黑盒、不稳定。
- **为什么**：优先排序是算术，不是智能；机会生成是唯一生成性步骤，用 LLM 但要 evidence-grounded。

**关键点：**

1. **business impact proxy = severity × frequency**（占位，真实业务影响需后续接入收益数据）。
2. **confidence 沿用 provisional 占位 0.5**（ADR-017）。
3. 只排 confirmed，candidate 保持 needs_review=True，待人工确认后再进入 ranking。

---

## ADR-019：Phase 7 评估框架与 baseline 结果

- **决策**：评估框架独立于 production code（`app/evaluation/` + `data/eval/`），用确定性 grader/metrics 反向验证 Phase 3–5。数据集 36 分类 + 18 聚类 + 6 优先级案例（手标 ground truth，版本化）。
- **备选方案**：只加单测；用 LLM-as-judge 评所有维度。
- **权衡**：确定性 grader 可复现、无偏差；LLM-as-judge 只在确定性不足处（命名）用。
- **为什么**：先测量 → 分析 failure → 提修改方案 → 人工 review，而非盲目改算法。

**Baseline 关键结论（见 `data/eval/results/baseline_v1.json`）：**

1. **分类是 mock**：accuracy 16.7%（FakeLLM 全返回 payment_failed），macro F1 0.026，other_rate 0%。分类评估需接入真实 LLM 才有意义。
2. **聚类 failure 复现**："Payment page froze."（checkout_stuck）在阈值 ≤ 0.75 时被并入 payment_failed；≥ 0.80 才分开。best F1/ARI 在 0.85（F1 0.67、ARI 0.65）。当前 0.75 会复现 failure case。
3. **优先级 p2/p3 互换**：系统把 "Apple Pay not working"（high, 15 条）排在 "Duplicate charge"（critical, 8 条）之上（spearman 0.94），根因是 impact = severity × frequency 与 severity/frequency 项重复计算。与 ADR-018 的 evaluation hypothesis 一致。

---

## ADR-020：Prioritisation V2（移除 impact 重复计算）

- **决策**：删除 `impact = severity × frequency` 项，公式改为 `w_s·severity_norm + w_f·frequency_norm + w_b·breadth_norm`，权重 severity=1.0 / frequency=1.0 / breadth=0.5。
- **备选方案**：保留 impact 但降权；改用 RICE 等框架。
- **权衡**：impact 项与 severity/frequency 项重复计算，虚高高频问题；去掉后更正交、可解释。
- **为什么**：这是 ADR-018 记录的 evaluation hypothesis，被 Phase 7 评估证实（p2/p3 互换）。

**评估验证（改善量化）：**

| 指标 | V1（含 impact） | V2（去 impact） |
|------|----------------|-----------------|
| Spearman | 0.9429 | **1.0** |
| system_order | p1,p3,p2,… | **p1,p2,p3,p4,p5,p6**（= human_order） |

关键变化：critical/8 条（重复扣费）现在排在 high/15 条（Apple Pay）之上，符合 PM 判断。

---

## ADR-021：Category-Aware Clustering（禁止跨 category 合并）

- **决策**：聚类加入 category-aware 硬约束——不同 `primary_category` 的反馈**永不合并**（跨类相似度设为 -1）。等价于"按 category 分组，组内再做 embedding 聚类"。
- **备选方案**：跨类加 penalty（软约束）；跨类要求更高阈值；完全靠 embedding（现状）。
- **权衡**：禁止最可解释、最符合 taxonomy 语义、零新超参；代价是 classification error 会被锁进错误组（缓解：94% 分类准确率 + needs_review 标记）。
- **为什么**：taxonomy 是"什么算同一问题"的权威定义，两个不同 category 的反馈本就不该合并；已确认的 failure case 正是跨类误合并导致。

**评估验证（阈值 0.75，DeepSeek 真实分类）：**

| 指标 | embedding-only（旧） | category-aware（新） |
|------|---------------------|---------------------|
| pairwise precision | 0.412 | **1.000** |
| pairwise recall | 0.700 | 0.700 |
| pairwise F1 | 0.518 | **0.824** |
| ARI | 0.475 | **0.814** |
| failure（Payment page froze 误并入 payment_failed） | ✅ 复现 | ❌ 全阈值消除 |

结论：failure case 消除，precision 0.412→1.0，recall 持平，最优 F1 从 0.85 档（0.667）移到 0.70 档（0.824）。
