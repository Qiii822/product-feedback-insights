"""机会生成 prompt（版本 v2）。

决策：机会建议必须 evidence-grounded——只基于给定问题描述与证据生成，
不得编造证据中没有的技术 root cause / business impact / 平台 / 客户群体。

v2 变更：新增 action_items（可执行修复步骤）与 success_metrics（验证指标），
让机会输出"可执行、可迭代"——读者看完知道第一步做什么、如何验证是否有效。
"""

PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """你是产品机会生成器。

给定一个产品问题及其支撑证据（客户反馈），生成一条可执行、可迭代的产品机会：

- title: 机会标题（一句话，点明要优化什么）
- summary: 一句话概述（这个问题为何重要、影响谁）
- recommendation: 具体建议——先给出基于证据的诊断方向，再明确第一步该做什么
  （如 "从支付失败日志入手，定位 Apple Pay 收银台在哪个环节中断"）
- action_items: 3~5 条可执行的修复/验证步骤（字符串列表，每条是一个具体动作，
  按先后顺序排列，例如排查日志 → 复现 → 修复 → 回归）
- success_metrics: 2~3 条可度量的验证指标（字符串列表，用于判断修复是否有效、
  支撑后续迭代，例如 "支付失败率下降"、"该问题相关投诉 7 天内归零"）
- expected_impact: 预期影响（基于证据量化，如 "减少支付失败类投诉"）

严格要求（evidence-grounded）：
1. 只基于给定的问题描述与证据，不得引入证据中没有的技术 root cause、business impact、平台或客户群体。
2. 不要编造具体技术原因（如"XX 服务宕机"）。
3. action_items / success_metrics 必须具体、可执行、可度量，不要写空泛的口号。

输出：只返回一个 JSON 对象，字段为 title / summary / recommendation / action_items / success_metrics / expected_impact。
"""


def build_opportunity_messages(problem, evidence_texts: list[str]) -> list[dict]:
    """构建机会生成用的 system + user 消息。"""
    evidence_block = "\n".join(f"- {t}" for t in evidence_texts) or "- （无证据）"
    user_content = (
        f"问题标题：{problem.title}\n"
        f"问题描述：{problem.description or '（无）'}\n"
        f"支撑证据：\n{evidence_block}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
