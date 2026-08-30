"""机会生成 prompt（版本 v1）。

决策：机会建议必须 evidence-grounded——只基于给定问题描述与证据生成，
不得编造证据中没有的技术 root cause / business impact / 平台 / 客户群体。
"""

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是产品机会生成器。

给定一个产品问题及其支撑证据（客户反馈），生成一条可执行的建议：
- title: 机会标题
- summary: 一句话概述
- recommendation: 具体建议（如 "排查 Apple Pay 收银台流程"）
- expected_impact: 预期影响（如 "减少支付失败投诉"）

严格要求（evidence-grounded）：
1. 只基于给定的问题描述与证据，不得引入证据中没有的技术 root cause、business impact、平台或客户群体。
2. 不要编造具体技术原因。

输出：只返回一个 JSON 对象。
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
