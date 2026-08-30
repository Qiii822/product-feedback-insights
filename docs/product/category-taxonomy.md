# 产品问题分类法（Taxonomy）最终规范 — 支付 / 收银台领域

> 状态：**最终定稿**（已 review）。取代 `category-taxonomy-proposal.md`。
> 本规范定义"反馈理解"阶段输出的 `primary_category` 受控词表，以及与之配套的分析维度。

---

## 1. 分析维度模型（analytical dimensions）

`primary_category` 只是一个分析维度，**不承载** severity、issue type、root cause 或 priority。

一条反馈（Feedback）的分析结果由以下**相互独立**的维度构成：

```
Feedback
 ├── primary_category   问题分类（本规范的 11 类）
 ├── issue_type         反馈类型（problem / request / question / feedback）
 ├── severity           严重程度（low / medium / high / critical，序数）
 ├── confidence         置信度（0~1，连续）
 ├── evidence           关联的证据（指向支撑该判断的原始反馈）
 └── needs_review       是否需要人工复核（bool）
```

- 各维度互不派生：例如 `issue_type = request` 的反馈，其 `severity` 可能很低；`primary_category = other` 的反馈，其 `issue_type` 可以是 `problem` 也可以是 `request`。
- 分类器只负责填 `primary_category` + `confidence` + `needs_review`；`severity` 与 `issue_type` 是另外的判定维度（Phase 3 一并产出，但彼此独立）。

---

## 2. `primary_category` 词表（11 类，flat）

采用**扁平（flat）**命名，不用层级点号。类别 ID 为英文下划线串（存储/代码用）。

```
Payment（支付）
  payment_declined              被拒付
  payment_failed                支付失败（通用 / 技术）
  payment_timeout               支付超时

Payment Method（支付方式）
  payment_method_missing        缺少支付方式
  payment_method_not_working    支付方式不可用

Checkout（收银台）
  checkout_stuck                收银台卡住
  checkout_crash                收银台崩溃
  checkout_performance          收银台性能（慢）

Billing（账单与扣费）
  duplicate_charge              重复扣费
  incorrect_charge              错误扣费

Fallback（兜底）
  other                         其他（out-of-domain / 无法归类）
```

**共 11 类。** MVP 目标是 taxonomy **一致性（consistency）**，不是**完备性（completeness）**；粒度暂不锁死，评估数据出现稳定且有产品意义的新 failure mode 时再增类。

---

## 3. 每个类目的详细说明

### 3.1 `payment_declined` — 被拒付

- **定义**：支付交易被发卡行 / 风控**明确拒绝**。
- **包含标准**：用户报告"被拒 / declined / 银行拒绝"，且用户认为该卡本应可用。
- **排除标准**：超时（→ `payment_timeout`）；系统报错（→ `payment_failed`）；缺少支付方式（→ `payment_method_missing`）。
- **正例**："The card was declined but I have money."
- **反例**："Payment timed out."（→ `payment_timeout`）；"Couldn't pay with Apple Pay."（→ `payment_method_not_working`）
- **边界情形**：若被拒明确由 3DS / 验证失败引起——约定：用户明确提到"验证失败"归 `payment_failed`；只提"被拒"归 `payment_declined`。

### 3.2 `payment_failed` — 支付失败（通用 / 技术）

- **定义**：支付交易因系统 / 技术错误而失败（非拒付、非超时、非缺方式）。
- **包含标准**：笼统的"支付失败 / 出错 / error / failed"，无更具体根因。
- **排除标准**：明确被拒（→ `payment_declined`）；明确超时（→ `payment_timeout`）；方式不可用（→ `payment_method_not_working`）；页面卡住（→ `checkout_stuck`）。
- **正例**："Payment failed again."
- **反例**："The card was declined."（→ `payment_declined`）；"Checkout keeps loading."（→ `checkout_stuck`）
- **边界情形**：3DS / 支付认证失败，**仅当明确导致支付无法完成时**归本类；若核心问题是收银台卡住 / 加载缓慢 / 性能，按实际症状归 `checkout_stuck` / `checkout_performance`，**不能仅因出现"3DS"就归本类**。MVP 不单列 authentication；未来 Evaluation 证明 3DS 反馈规模足够、分类稳定、且具独立产品决策价值时，再考虑拆出独立类。

### 3.3 `payment_timeout` — 支付超时

- **定义**：支付请求因**超时**未完成。
- **包含标准**：明确提到"超时 / timed out / 卡在支付处理中很久后失败"。
- **排除标准**：页面加载慢但未发起交易（→ `checkout_performance`）；被拒（→ `payment_declined`）。
- **正例**："Payment timed out after 5 minutes."
- **反例**："Checkout page loads slowly."（→ `checkout_performance`）
- **边界情形**："等了很久然后失败"但未明确"超时" → 归 `payment_failed`。

### 3.4 `payment_method_missing` — 缺少支付方式

- **定义**：用户**找不到**想用的支付方式（选项不存在）。
- **包含标准**："没有 Apple Pay 选项 / 只支持 X / 为什么不能用 Y"。
- **排除标准**：方式存在但用不了（→ `payment_method_not_working`）。
- **正例**："Why is there no PayPal option?"
- **反例**："Apple Pay button does nothing."（→ `payment_method_not_working`）
- **边界情形**：此类常伴随 `issue_type = request`（feature request 而非缺陷）。

### 3.5 `payment_method_not_working` — 支付方式不可用

- **定义**：支付方式**存在但无法正常使用**（点击无反应、报错、流程走不通）。
- **包含标准**："Apple Pay 用不了 / 点了没反应 / 卡在验证"。
- **排除标准**：方式不存在（→ `payment_method_missing`）；交易被拒（→ `payment_declined`）。
- **正例**："Couldn't pay with Apple Pay."；"Apple Pay button does nothing."
- **反例**："There's no Apple Pay option."（→ `payment_method_missing`）
- **边界情形**："Apple Pay 点了跳到空白页" → 根因是页面问题归 `checkout_stuck`，根因是集成问题归本类。

### 3.6 `checkout_stuck` — 收银台卡住

- **定义**：收银台**无法继续推进**（冻结、无限加载、spinner 不停）。
- **包含标准**：冻结 / 卡住 / 无限加载 / spinner 一直转 / 无法完成 checkout。
- **排除标准**：应用崩溃退出（→ `checkout_crash`）；慢但能完成（→ `checkout_performance`）。
- **正例**："Checkout keeps loading."；"Payment page froze."
- **反例**："The app crashes when I tap Pay."（→ `checkout_crash`）；"Checkout is slow but eventually works."（→ `checkout_performance`）
- **边界情形**：`frozen` 与 `stuck` **已合并**为本类；暂不拆分，评估显示两者是稳定且有产品意义的不同 failure mode 时再考虑。

### 3.7 `checkout_crash` — 收银台崩溃

- **定义**：应用在 **checkout / payment 上下文**中崩溃 / 闪退。
- **包含标准**：明确发生在 checkout/payment 上下文中的崩溃（如"点击 Pay 时崩溃"）。
- **排除标准**：无 checkout 上下文的泛化崩溃（→ `other`）。
- **正例**："The app crashes when I tap Pay."
- **反例**："The app crashes when I open Settings."（→ `other`）；"The app keeps crashing."（→ `other`）
- **边界情形**：崩溃上下文不清 → 归 `other`。**不设泛化 crash 类**，避免领域从 Payments/Checkout 扩张到 General App Reliability。

### 3.8 `checkout_performance` — 收银台性能（慢）

- **定义**：收银台缓慢 / 卡顿，但**仍能推进完成**（非完全卡住）。
- **包含标准**：慢 / 卡顿 / 加载慢，但最终能完成 checkout。
- **排除标准**：完全卡住无法推进（→ `checkout_stuck`）；崩溃（→ `checkout_crash`）。
- **正例**："Checkout page takes forever to load but eventually works."
- **反例**："Checkout keeps loading and never finishes."（→ `checkout_stuck`）
- **边界情形**："慢"与"卡住"的判据是**能否推进完成**；不能完成 → `checkout_stuck`。

### 3.9 `duplicate_charge` — 重复扣费

- **定义**：同一笔订单被**扣了多次**。
- **包含标准**："被扣两次 / charged twice / double charged"。
- **排除标准**：金额 / 项目不对但只扣一次（→ `incorrect_charge`）。
- **正例**："Was charged twice for one order."
- **反例**："I was charged the wrong amount."（→ `incorrect_charge`）
- **边界情形**：订阅**周期内**的正常续费被误认为重复扣费 → 需结合订阅逻辑判断。

### 3.10 `incorrect_charge` — 错误扣费

- **定义**：扣费**金额 / 项目**与预期不符（不该扣、扣多了、扣错项目）。
- **包含标准**："续费后还在扣 / 被多收 / 金额不对 / 取消后仍被收费"。
- **排除标准**：同一订单重复扣（→ `duplicate_charge`）。
- **正例**："Subscription renewed after I cancelled."
- **反例**："Was charged twice for one order."（→ `duplicate_charge`）
- **边界情形**："取消后仍扣费"若用户**已在等退款** → 归 `other` + 用 `issue_type` 表达。

### 3.11 `other` — 其他（兜底）

- **定义**：无法归入上述 10 类的反馈（out-of-domain、缺少上下文、退款等）。
- **包含标准**：明确 out-of-domain（如非收银台的崩溃）、缺少上下文无法归类、退款请求、账号 / 物流等非支付问题。
- **排除标准**：能明确归入 1–10 类（不把 `other` 当默认）。
- **正例**："The app crashes when I open Settings."；"I want a refund."
- **反例**："Payment failed again."（→ `payment_failed`）
- **边界情形**：**退款相关一律归 `other`**，通过 `issue_type` 区分（见 §4）。

---

## 4. `issue_type` 维度

独立于 `primary_category` 的反馈类型维度，取值：

| issue_type | 含义 | 示例 |
|------------|------|------|
| `problem` | 用户遇到了问题 / 故障 | "My refund hasn't arrived." |
| `request` | 用户提出请求 / 需求 | "I want a refund."；"Please add PayPal." |
| `question` | 用户提问 | "How do I get a refund?" |
| `feedback` | 一般性反馈 / 建议（非问题、非请求、非提问） | "The checkout looks great." |

**退款规则**：退款不设 primary_category；退款反馈的 `primary_category = other`，用 `issue_type` 区分——"我要退款"（`request`）vs "退款没到账"（`problem`）。

**维度独立性**：`issue_type` 是独立维度，**不决定** `primary_category`。例如：

- "I want Apple Pay to be supported." → `primary_category = payment_method_missing`、`issue_type = request`
- "Can I pay with Apple Pay?" → `primary_category = payment_method_missing`、`issue_type = question`

不要因为 `issue_type` 是 `request` / `question` 就自动把 `primary_category` 设为 `other`。

---

## 5. 单标签与不确定性

- **单 primary_category**：每条反馈只有一个 `primary_category`，不实现 multi-label。
- 一条反馈涉及多个问题、且难以取舍时：**不强行拆多标签**，而是给出**较低 `confidence`** 并置 **`needs_review = true`**，交由人工复核。

---

## 6. `other` 的评估规则

- `other` 是**正式评估类别**（不是"没分类"）。
- 评估中**单独统计**：
  - `other` precision（归为 other 的反馈里，真正该归 other 的占比）
  - `other` recall（真正该归 other 的反馈里，被正确归入 other 的占比）
  - overall other rate（整体 other 占比）
- 目标：既**不把 `other` 当作模型逃避分类的默认选项**，也**不强迫**明显 out-of-domain 或 ambiguous 的反馈挤进具体类别。

---

## 7. 分类映射示例（基于 sample_feedback.csv）

| 示例反馈 | primary_category | issue_type |
|----------|-----------------|------------|
| "Payment failed again." | `payment_failed` | `problem` |
| "Couldn't pay with Apple Pay." | `payment_method_not_working` | `problem` |
| "Apple Pay button does nothing." | `payment_method_not_working` | `problem` |
| "The card was declined but I have money." | `payment_declined` | `problem` |
| "Checkout keeps loading." | `checkout_stuck` | `problem` |
| "Payment page froze." | `checkout_stuck` | `problem` |
| "App crashed during checkout." | `checkout_crash` | `problem` |
| "Was charged twice for one order." | `duplicate_charge` | `problem` |
| "Subscription renewed after I cancelled." | `incorrect_charge` | `problem` |
| "The app crashes when I open Settings." | `other` | `problem` |
| "I want a refund." | `other` | `request` |
| "My refund hasn't arrived." | `other` | `problem` |

---

## 8. 落地说明（Phase 3 起）

- 11 个 category ID 与 4 个 issue_type 值将作为 `FeedbackAnalysis` 的合法取值（受控词表 / 枚举）。
- 分类器（LLM）输出需满足：单 `primary_category` ∈ 词表、`issue_type` ∈ 词表、`confidence` ∈ [0,1]、`needs_review` ∈ bool；否则视为非法输出。
- 词表先作为常量落盘，Phase 3 实现时再决定放 `schemas/enums.py` 还是独立模块。
