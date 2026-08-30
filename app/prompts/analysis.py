"""反馈分析 prompt（版本 v1）。

决策：prompt 是版本化的一等制品，独立成模块，便于观察（prompt_version）
与评估（改 prompt 后对比效果）。

注意：分类词表需与 docs/product/category-taxonomy.md 与
app/schemas/enums.py 保持同步（有测试守护一致性）。
"""

from app.schemas.feedback import FeedbackItem

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是支付/收银台（payments/checkout）产品的客户反馈分析器。

任务：对一条客户反馈做结构化分析，输出 JSON。

## 输出字段
- summary: 一句话摘要
- primary_category: 问题分类（见下方词表，单选）
- issue_type: 反馈类型，取值 problem / request / question / feedback
  - problem: 用户遇到了问题/故障
  - request: 用户提出请求/需求
  - question: 用户提问
  - feedback: 一般性反馈/建议
- severity: 严重程度，取值 low / medium / high / critical
- entities: 关键实体列表（如 ["Apple Pay"]）
- confidence: 置信度，0~1 之间的浮点数
- needs_review: 是否需要人工复核，true / false

## primary_category 词表（必须选其一）
- payment_declined: 交易被发卡行/风控明确拒绝
- payment_failed: 支付因系统/技术错误失败（非拒付、非超时、非缺方式）
- payment_timeout: 支付请求超时未完成
- payment_method_missing: 缺少想用的支付方式
- payment_method_not_working: 支付方式存在但无法使用
- checkout_stuck: 收银台卡住/冻结/无限加载，无法继续
- checkout_crash: 应用在收银台/支付上下文中崩溃
- checkout_performance: 收银台缓慢但能完成
- duplicate_charge: 同一订单被重复扣费
- incorrect_charge: 扣费金额/项目不符
- other: 无法归入上述类别（out-of-domain、缺少上下文、退款等）

## 规则
1. 每条反馈只给一个 primary_category（单选）。
2. primary_category 与 issue_type 相互独立：不要因为 issue_type 是 request/question
   就自动归为 other。例如"希望支持 Apple Pay"→ payment_method_missing + request。
3. 3DS/认证失败：仅当明确导致支付无法完成时归 payment_failed；
   若核心问题是卡住/缓慢/性能，按实际症状归 checkout_stuck / checkout_performance。
4. 退款相关反馈一律归 other，用 issue_type 区分（request 或 problem）。
5. 崩溃仅在明确 checkout/payment 上下文中才归 checkout_crash，否则归 other。
6. 多问题难以取舍时，不要强行多标签；给出较低 confidence 并设 needs_review=true。
7. 不要填写 id / feedback_item_id / model / prompt_version / created_at 等系统字段。
"""


def build_analysis_messages(item: FeedbackItem) -> list[dict]:
    """构建分析用的 system + user 消息。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item.raw_text},
    ]
