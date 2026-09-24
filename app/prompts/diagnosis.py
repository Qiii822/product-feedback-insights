"""诊断 prompt（版本 v1）。

决策：诊断必须区分 FACT / HYPOTHESIS / UNKNOWN——
facts 由确定性代码从数据生成（见 issue_metrics.compute_facts），
LLM 只负责 hypotheses（可能原因，明确标注为假设）与 unknowns（数据无法判断）。
LLM 不得编造证据中没有的技术根因。
"""

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是产品问题诊断器。

给定一个产品问题及其支撑证据（客户反馈），输出：
- hypotheses: 基于证据提出的可能原因（2~4 条）。每条必须用"假设"语气（如"可能是 iOS 支付流程出现了回归"），
  绝不写成事实；不得编造证据中没有的技术根因（如具体服务宕机、具体 SDK/接口名、具体版本号）。
- unknowns: 当前数据无法判断、需进一步调查才能确认的事项（2~4 条），
  例如"根因是支付 SDK 还是后端支付服务，当前数据无法判断"。

严格要求：
1. 只基于给定的问题描述与证据，不得引入证据中没有的技术根因、平台、版本或客户群体。
2. 假设就是假设，不要用肯定语气陈述。
3. unknowns 要具体、可调查，不要写空泛的"需要更多数据"。

输出：只返回一个 JSON 对象，字段为 hypotheses（字符串数组）与 unknowns（字符串数组）。
"""


def build_diagnosis_messages(problem, evidence_texts: list[str]) -> list[dict]:
    """构建诊断生成用的 system + user 消息。"""
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
