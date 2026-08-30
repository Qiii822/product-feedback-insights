"""聚类命名 prompt（版本 v1）。

决策：聚类命名用 LLM，但必须 evidence-grounded——只基于给定代表性反馈归纳，
不得引入反馈中没有证据支持的技术 root cause、business impact 或其他事实。
"""

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是产品问题命名器。

给定一个聚类中的代表性客户反馈，为这个聚类生成：
- title: 简洁的问题标题（如 "支付失败"、"Apple Pay 不可用"）
- description: 一句话的问题描述

严格要求（evidence-grounded）：
1. 只基于给定的反馈文本归纳，不得引入技术 root cause、business impact 等反馈中没有证据支持的事实。
2. 不要编造具体技术原因（如"XX 服务宕机"）。
3. 不要臆测用户群体或平台。

输出：只返回一个 JSON 对象，包含 title 与 description 字段。
"""


def build_naming_messages(representative_texts: list[str]) -> list[dict]:
    """构建命名用的 system + user 消息。"""
    user_content = "\n".join(f"- {t}" for t in representative_texts)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
