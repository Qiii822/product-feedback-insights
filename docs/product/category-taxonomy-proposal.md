# 产品问题分类法（Taxonomy）Proposal — 支付 / 收银台领域

> 状态：**已被取代**。最终规范见 [`category-taxonomy.md`](category-taxonomy.md)。本文保留作提案历史。
> 依据：当前 `data/raw/sample_feedback.csv` 的示例反馈 + MVP 目标（把非结构化反馈转化为有证据的产品洞察）。

---

## 0. 目的与范围

分类法（taxonomy）是"反馈理解"阶段输出的 `category` 字段的**受控词表**。它的作用是：

1. 让聚类与排序在一个**稳定、可解释**的类别集合上工作，而不是自由文本标签。
2. 让问题识别能按"同一类问题"聚合 frequency（例如"支付失败"这一类有多少条证据）。
3. 让 LLM 的分类输出可被**确定性 grader** 校验（分类对了没有）。

**范围**：仅覆盖 MVP 的支付/收银台（payments / checkout）领域。不覆盖账号、物流、商品等其他领域。

---

## 1. 设计原则

1. **层级化（hierarchical），而非扁平列表**：两级结构——第一级是大类（Level 1），第二级是叶子类目（Level 2，真正用于分类）。
2. **点号编码**：用点号拼接表示层级，如 `payment_failure.declined`。好处：
   - 可存进单个字符串字段（`FeedbackAnalysis.category`），无需额外表。
   - 可按前缀聚合到 Level 1（`startswith("payment_failure")` → 支付失败大类）。
   - 人类可读、评审直观。
3. **叶子互斥、层级可聚合**：一条反馈最终标一个叶子类目；但报告时既可看叶子，也可看大类。
4. **可扩展**：新增类目只需加一个点号编码，不破坏现有类目。

---

## 2. 分类法总览

```
payment_failure           支付失败
├── declined              被拒付
├── technical             技术故障
└── timeout               超时

payment_method            支付方式
├── missing               缺少支付方式
└── not_working           支付方式不可用

billing                   账单与扣费
├── duplicate_charge      重复扣费
└── incorrect_charge      错误扣费

refund                    退款
├── requested             申请退款
└── not_received          退款未到账

authentication            认证与验证
└── 3ds_verification      3DS / 验证问题

checkout_performance      收银台性能与可用性
├── stuck                 卡住 / 加载缓慢
├── frozen                页面冻结
└── crash                 崩溃
```

---

## 3. 每个类目的详细说明

### 3.1 `payment_failure` — 支付失败

支付**交易本身失败或报错**（用户发起了支付，但没有成功）。

#### 3.1.1 `payment_failure.declined` — 被拒付

- **定义**：交易被发卡行 / 风控明确**拒绝**。
- **包含标准**：用户报告"卡被拒 / 被拒绝 / declined / 银行拒绝"，但用户认为卡应可用。
- **排除标准**：因超时、系统报错导致的失败（归 `technical` / `timeout`）；缺支付方式（归 `payment_method.missing`）。
- **正例**："The card was declined but I have money."（示例 fb_006）
- **边界情形**："declined because of 3DS verification" → 归 `authentication.3ds_verification`，因为根因是验证而非拒付。
- **优先级排序适配**：**高**。直接损失交易，且常指向风控误杀，值得立即排查。

#### 3.1.2 `payment_failure.technical` — 技术故障

- **定义**：支付过程因系统/技术错误而失败（非拒付、非超时、非缺方式）。
- **包含标准**：笼统的"支付失败 / payment failed / 出错 / error"，无更具体根因。
- **排除标准**：能明确归到"被拒付"（→`declined`）、"超时"（→`timeout`）、"方式不可用"（→`payment_method.not_working`）、"页面卡住"（→`checkout_performance.stuck`）。
- **正例**："Payment failed again."（示例 fb_001/008/011/014）
- **边界情形**：这是**兜底粒度最粗**的类，天然高频。Phase 3 后若某子根因（如某网关）反复出现，可再拆分。
- **优先级排序适配**：**高**。高频 + 高模糊度，是聚类后最需要深挖的一类。

#### 3.1.3 `payment_failure.timeout` — 超时

- **定义**：支付请求因**超时**未完成。
- **包含标准**：明确提到"超时 / timed out / 卡在支付处理中很久后失败"。
- **排除标准**：页面加载慢但最终未发起交易（→`checkout_performance.stuck`）。
- **正例**："Payment timed out after 5 minutes."
- **边界情形**：用户说"等了很久然后失败"，若未明确"超时"，优先归 `technical`。
- **优先级排序适配**：**高**。通常指向后端/网关延迟或超时配置问题。

---

### 3.2 `payment_method` — 支付方式

问题与**特定支付方式（Apple Pay、信用卡等）的可用性**相关。

#### 3.2.1 `payment_method.missing` — 缺少支付方式

- **定义**：用户**找不到**想用的支付方式（选项不存在）。
- **包含标准**："没有 Apple Pay 选项 / 只支持 X / 为什么不能用 Y"。
- **排除标准**：方式**存在但用不了**（→`not_working`）。
- **正例**："Why is there no PayPal option?"
- **边界情形**：这常常是**需求/feature request**而非缺陷。
- **优先级排序适配**：**中**。更偏向产品覆盖度决策，而非故障。

#### 3.2.2 `payment_method.not_working` — 支付方式不可用

- **定义**：支付方式**存在但无法正常使用**（点了没反应、报错、流程走不通）。
- **包含标准**："Apple Pay 用不了 / 点了没反应 / 卡在验证"。
- **排除标准**：方式不存在（→`missing`）；交易被拒（→`payment_failure.declined`）。
- **正例**："Couldn't pay with Apple Pay."（fb_002/005）；"Apple Pay button does nothing."（fb_009）
- **边界情形**："Apple Pay 点了跳到空白页" → 若根因是页面问题，可能归 `checkout_performance`；若根因是 Apple Pay 集成，归本类。
- **优先级排序适配**：**高**。特定方式不可用会直接阻塞交易，且可定位到集成/兼容性问题。

---

### 3.3 `billing` — 账单与扣费

问题与**扣费金额/次数的正确性**相关。

#### 3.3.1 `billing.duplicate_charge` — 重复扣费

- **定义**：同一笔订单被**扣了多次**。
- **包含标准**："被扣了两次 / charged twice / double charged"。
- **排除标准**：金额不对但只扣一次（→`incorrect_charge`）。
- **正例**："Was charged twice for one order."（fb_010）
- **边界情形**：订阅**周期内**的正常续费被误认为是重复扣费 → 需结合订阅逻辑判断。
- **优先级排序适配**：**高**。金钱损失 + 信任危机，通常需紧急处理。

#### 3.3.2 `billing.incorrect_charge` — 错误扣费

- **定义**：扣费**金额/项目**与预期不符（不该扣、扣多了、扣错项目）。
- **包含标准**："续费后还在扣 / 被多收 / 收费金额不对 / 取消后仍被收费"。
- **排除标准**：同一订单重复扣（→`duplicate_charge`）。
- **正例**："Subscription renewed after I cancelled."（fb_012）
- **边界情形**："取消后仍被收费"可能是退款问题（若用户已在等退款 → 归 `refund.not_received`）。
- **优先级排序适配**：**高**。涉及信任与合规。

---

### 3.4 `refund` — 退款

问题与**退款申请与到账**相关。

#### 3.4.1 `refund.requested` — 申请退款

- **定义**：用户**主动请求退款**（意图表达，未必有故障）。
- **包含标准**："我要退款 / 请退款 / 怎么退款"。
- **排除标准**：已有故障且退款是附带诉求（优先归故障类，退款作为附加标签——见开放问题 4）。
- **正例**："I want a refund for this order."
- **边界情形**：这不是"缺陷"，而是**流程/意图**。是否纳入"产品问题"取决于你们对"问题"的定义。
- **优先级排序适配**：**中**。单条退款请求不是缺陷信号；但**高频退款 + 某类目强相关**是强信号。

#### 3.4.2 `refund.not_received` — 退款未到账

- **定义**：已申请/已批准退款，但**钱未到账**。
- **包含标准**："退款没收到 / 已经 7 天了还没退款"。
- **排除标准**：还没申请退款（→`requested`）。
- **正例**："My refund hasn't arrived after a week."
- **边界情形**：与 `billing.incorrect_charge` 有重叠（"多扣了 → 请退款"），需约定主类。
- **优先级排序适配**：**高**。退款流程断裂是明确的体验/信任缺陷。

---

### 3.5 `authentication` — 认证与验证

问题与**支付前的身份验证（3DS、短信、银行验证）**相关。

#### 3.5.1 `authentication.3ds_verification` — 3DS / 验证问题

- **定义**：3DS / 强客户认证（SCA）/ 验证码等**验证步骤**阻塞或失败。
- **包含标准**："卡在 3DS / 收不到验证码 / 验证一直失败"。
- **排除标准**：验证通过后被拒付（→`payment_failure.declined`）。
- **正例**："Stuck on 3DS verification screen."
- **边界情形**：3DS 失败后被拒付，根因是风控还是验证 UI，需人工判例。
- **优先级排序适配**：**高**。验证是合规必经环节，卡住会系统性阻断交易。

---

### 3.6 `checkout_performance` — 收银台性能与可用性

问题与**收银台页面的响应性、稳定性**相关（页面本身的问题，而非交易结果）。

#### 3.6.1 `checkout_performance.stuck` — 卡住 / 加载缓慢

- **定义**：页面**持续加载、卡住、无响应**，交易无法继续推进。
- **包含标准**："一直加载 / 卡住 / 转圈不停 / 太慢"。
- **排除标准**：页面冻结/崩溃（→`frozen` / `crash`）；明确超时后失败（→`payment_failure.timeout`）。
- **正例**："Checkout keeps loading."（fb_003/007）
- **边界情形**："一直加载最后失败" → 归本类（体验问题是主诉），而非 `payment_failure`。
- **优先级排序适配**：**高**。页面卡住 = 转化率直接受损。

#### 3.6.2 `checkout_performance.frozen` — 页面冻结

- **定义**：页面**完全冻结**（无加载动画、无响应），需重启/刷新。
- **包含标准**："页面冻住 / froze / 完全没反应"。
- **排除标准**：仍在转圈加载（→`stuck`）；进程退出（→`crash`）。
- **正例**："Payment page froze."（fb_004）
- **边界情形**："冻住"与"卡住"语义接近，可能需要合并为 `stuck`（见开放问题 2）。
- **优先级排序适配**：**高**。

#### 3.6.3 `checkout_performance.crash` — 崩溃

- **定义**：应用在收银台**崩溃/闪退**。
- **包含标准**："崩溃 / 闪退 / app 关了"。
- **排除标准**：冻结但不退出（→`frozen`）。
- **正例**："App crashed during checkout."（fb_013）
- **边界情形**：崩溃可能属于**应用稳定性**（超出收银台领域），是否纳入本分类法需决策（见开放问题 1）。
- **优先级排序适配**：**中~高**。崩溃需日志定位，但"崩溃"本身信息量低，需聚类细分。

---

## 4. 示例反馈 → 建议分类（grounding）

| 示例反馈 | 建议叶子类目 |
|----------|-------------|
| "Payment failed again." | `payment_failure.technical` |
| "Couldn't pay with Apple Pay." | `payment_method.not_working` |
| "Checkout keeps loading." | `checkout_performance.stuck` |
| "Payment page froze." | `checkout_performance.frozen` |
| "The card was declined but I have money." | `payment_failure.declined` |
| "Apple Pay button does nothing." | `payment_method.not_working` |
| "Was charged twice for one order." | `billing.duplicate_charge` |
| "Subscription renewed after I cancelled." | `billing.incorrect_charge` |
| "App crashed during checkout." | `checkout_performance.crash`（或有争议，见开放问题） |

> 说明：示例数据里没有 refund / authentication / payment_method.missing / timeout 的真实样本，这些类目是**按领域知识预置**的，未来有数据再校准。

---

## 5. 边界与开放问题（需要你 review 决策）

1. **`checkout_performance.crash` 是否纳入？** 崩溃可能属于"应用稳定性"而非"收银台"领域。若纳入，Phase 3 的 LLM 分类需要明确的领域边界指令。
2. **`frozen` 与 `stuck` 是否合并？** 二者语义接近，LLM 可能难以稳定区分。建议 MVP 先合并为 `checkout_performance.stuck`，待评估显示有必要再拆。
3. **`refund` 是否属于 MVP 的"产品问题"？** `refund.requested` 是流程/意图而非缺陷。若你们的目标是"发现缺陷"，可暂时把 refund 降为"附加标签"而非主类目。
4. **单标签 vs 多标签？** 当前设计是**单叶子类目**（互斥）。但真实反馈常多因（"多扣了钱，还退款没到账"）。是否允许一条反馈命中多个类目？（影响 schema 与 grader 设计。）
5. **是否需要 `other` 兜底类？** 若出现无法归类的反馈，是归 `other`，还是强制归到最接近的类目？（影响分类准确率度量。）
6. **类目粒度的最终确认**：Level 2 的 14 个叶子类目是否过细/过粗？例如 `payment_failure.technical` 是否需要按网关再拆。

---

## 6. 建议的下一步

1. 你对上述分类法（尤其第 5 节开放问题）给出取舍。
2. 我据此把分类法定稿为受控词表（`app/schemas/enums.py` 或独立常量模块），作为 Phase 3 的 `FeedbackAnalysis.category` 合法取值。
3. 定稿后再进入 Phase 3 的"单条反馈分析"实现。
