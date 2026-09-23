"""LLM 客户端实现。

- FakeLLM / NullLLM：确定性 mock（单元测试、无网络环境）。
- DeepSeekProvider：真实 DeepSeek（OpenAI 兼容 API）。

embedding 已拆分为独立的 EmbeddingProvider（见 embedding.py）。
"""

import json
import time

from app.core.errors import LLMOutputError, LLMProviderError
from app.schemas.analysis import FeedbackAnalysis
from app.schemas.clustering import ClusterNaming
from app.schemas.enums import IssueType, PrimaryCategory, Severity
from app.schemas.opportunity import ProductOpportunity
from app.services.interfaces import LLMClient


def _user_text(messages: list) -> str:
    """拼接 messages 里所有 user 消息内容（小写），供 FakeLLM 做关键词接地。"""
    parts = []
    for m in messages or []:
        if isinstance(m, dict) and m.get("role") == "user":
            parts.append(str(m.get("content", "")))
    return "\n".join(parts).lower()


# 关键词分类规则（顺序即优先级）：(关键词元组, category, severity, issue_type)
_CLASSIFY_RULES: list[tuple[tuple[str, ...], PrimaryCategory, Severity, IssueType]] = [
    (("refund", "delete my account", "how do i", "great app"), PrimaryCategory.OTHER, Severity.LOW, IssueType.REQUEST),
    (("declined", "rejected by", "bank"), PrimaryCategory.PAYMENT_DECLINED, Severity.HIGH, IssueType.PROBLEM),
    (("timed out", "timeout"), PrimaryCategory.PAYMENT_TIMEOUT, Severity.HIGH, IssueType.PROBLEM),
    (("crash",), PrimaryCategory.CHECKOUT_CRASH, Severity.CRITICAL, IssueType.PROBLEM),
    (("twice", "double", "charged again", "two times", "billed two times"), PrimaryCategory.DUPLICATE_CHARGE, Severity.CRITICAL, IssueType.PROBLEM),
    (("wrong amount", "wrong plan", "never signed up", "free plan", "renewed"), PrimaryCategory.INCORRECT_CHARGE, Severity.HIGH, IssueType.PROBLEM),
    (("no paypal", "not listed", "isn't listed", "why is there no", "can i pay", "please add", "crypto"), PrimaryCategory.PAYMENT_METHOD_MISSING, Severity.MEDIUM, IssueType.REQUEST),
    (("apple pay", "google pay", "paypal"), PrimaryCategory.PAYMENT_METHOD_NOT_WORKING, Severity.HIGH, IssueType.PROBLEM),
    (("slow", "lags", "lag", "takes forever", "eventually works"), PrimaryCategory.CHECKOUT_PERFORMANCE, Severity.LOW, IssueType.PROBLEM),
    (("stuck", "loading", "froze", "frozen", "spinner", "white screen"), PrimaryCategory.CHECKOUT_STUCK, Severity.HIGH, IssueType.PROBLEM),
]

_SUMMARY: dict[PrimaryCategory, str] = {
    PrimaryCategory.PAYMENT_FAILED: "支付失败",
    PrimaryCategory.PAYMENT_DECLINED: "银行卡被拒",
    PrimaryCategory.PAYMENT_TIMEOUT: "支付超时",
    PrimaryCategory.PAYMENT_METHOD_MISSING: "缺少支付方式",
    PrimaryCategory.PAYMENT_METHOD_NOT_WORKING: "支付方式不可用",
    PrimaryCategory.CHECKOUT_STUCK: "收银台卡住",
    PrimaryCategory.CHECKOUT_CRASH: "收银台崩溃",
    PrimaryCategory.CHECKOUT_PERFORMANCE: "收银台缓慢",
    PrimaryCategory.DUPLICATE_CHARGE: "重复扣费",
    PrimaryCategory.INCORRECT_CHARGE: "扣费金额不符",
    PrimaryCategory.OTHER: "其他反馈",
}

_CLUSTER_TITLE: dict[PrimaryCategory, str] = {
    PrimaryCategory.PAYMENT_FAILED: "支付失败",
    PrimaryCategory.PAYMENT_DECLINED: "银行卡被拒",
    PrimaryCategory.PAYMENT_TIMEOUT: "支付超时",
    PrimaryCategory.PAYMENT_METHOD_MISSING: "缺少常用支付方式",
    PrimaryCategory.PAYMENT_METHOD_NOT_WORKING: "移动支付方式不可用",
    PrimaryCategory.CHECKOUT_STUCK: "收银台卡住/无限加载",
    PrimaryCategory.CHECKOUT_CRASH: "收银台崩溃",
    PrimaryCategory.CHECKOUT_PERFORMANCE: "收银台加载缓慢",
    PrimaryCategory.DUPLICATE_CHARGE: "重复扣费",
    PrimaryCategory.INCORRECT_CHARGE: "扣费金额/项目不符",
    PrimaryCategory.OTHER: "其他反馈",
}

_CLUSTER_DESC: dict[PrimaryCategory, str] = {
    PrimaryCategory.PAYMENT_FAILED: "用户在下单支付时遇到失败，交易无法完成。",
    PrimaryCategory.PAYMENT_DECLINED: "银行卡被发卡行或风控拒绝，用户有余额仍被拒。",
    PrimaryCategory.PAYMENT_TIMEOUT: "支付请求超时未完成，用户等待后放弃。",
    PrimaryCategory.PAYMENT_METHOD_MISSING: "用户想用某支付方式但收银台未提供。",
    PrimaryCategory.PAYMENT_METHOD_NOT_WORKING: "已提供的支付方式无法使用或报错。",
    PrimaryCategory.CHECKOUT_STUCK: "收银台卡住/冻结/无限加载，无法继续支付。",
    PrimaryCategory.CHECKOUT_CRASH: "应用在支付/收银台上下文中崩溃。",
    PrimaryCategory.CHECKOUT_PERFORMANCE: "收银台加载缓慢，但最终能完成。",
    PrimaryCategory.DUPLICATE_CHARGE: "同一订单被重复扣费。",
    PrimaryCategory.INCORRECT_CHARGE: "扣费金额或项目与预期不符。",
    PrimaryCategory.OTHER: "无法归入支付/收银台类的其他反馈。",
}

# 机会模板：category → 可执行的建议 + 步骤 + 验证指标（evidence-grounded 的 mock 版本）
_OPPORTUNITY: dict[PrimaryCategory, dict] = {
    PrimaryCategory.PAYMENT_FAILED: {
        "title": "定位并降低支付失败率",
        "summary": "多个用户在下单时支付失败，直接阻断成单。",
        "recommendation": "从支付失败日志入手，定位失败集中在哪个环节（网关/收银台/参数）。",
        "action_items": [
            "汇总失败订单，按错误码/渠道/版本聚合定位高发环节",
            "复现高频失败路径，对比正常订单的请求差异",
            "针对根因修复并加失败重试/降级提示",
            "灰度发布并回归验证",
        ],
        "success_metrics": ["支付失败率下降", "失败后可重试成功率提升", "支付失败类投诉 7 天内下降"],
        "expected_impact": "减少支付失败投诉，挽回流失订单",
    },
    PrimaryCategory.PAYMENT_DECLINED: {
        "title": "降低银行卡误拒率",
        "summary": "用户有余额却被发卡行/风控拒绝，属正常交易被误拒。",
        "recommendation": "排查风控阈值与发卡行返回码，识别正常交易被误拒的环节。",
        "action_items": [
            "汇总被拒订单的发卡行与拒绝码分布",
            "与收单侧核对风控阈值，复现典型误拒场景",
            "对误拒用户提供换卡/重试/联系客服引导",
            "上线后监控误拒率变化",
        ],
        "success_metrics": ["误拒率下降", "被拒后重试成功率提升", "相关投诉 7 天内下降"],
        "expected_impact": "减少被拒投诉，挽回被误拒的订单",
    },
    PrimaryCategory.PAYMENT_TIMEOUT: {
        "title": "缩短支付超时时间",
        "summary": "用户支付请求超时未完成，长时间等待后放弃。",
        "recommendation": "排查支付链路中的慢节点与超时配置，缩短用户等待。",
        "action_items": [
            "统计超时订单在各环节的耗时分布",
            "定位慢节点（网关回调/第三方/前端轮询）",
            "优化超时配置并增加进度反馈",
            "灰度验证超时率变化",
        ],
        "success_metrics": ["支付平均耗时下降", "超时率下降", "超时后放弃率下降"],
        "expected_impact": "减少用户等待放弃，提升成单率",
    },
    PrimaryCategory.PAYMENT_METHOD_MISSING: {
        "title": "补齐常用支付方式",
        "summary": "用户想要 Apple Pay / Google Pay / PayPal 等但收银台未提供。",
        "recommendation": "按反馈提及频率排序，优先接入需求量最大的支付方式。",
        "action_items": [
            "统计各支付方式的需求量（Apple Pay / Google Pay / PayPal / 加密货币）",
            "评估接入成本与合规，确定优先级",
            "接入并灰度放量",
            "上线后收集使用量与转化反馈",
        ],
        "success_metrics": ["新增支付方式使用率", "收银台转化率提升", "相关需求类反馈下降"],
        "expected_impact": "覆盖更多用户偏好，提升收银台转化",
    },
    PrimaryCategory.PAYMENT_METHOD_NOT_WORKING: {
        "title": "修复移动支付方式不可用",
        "summary": "Apple Pay / Google Pay / PayPal 等已提供但无法使用或报错。",
        "recommendation": "排查不可用支付方式的报错日志，定位是配置、证书还是接口问题。",
        "action_items": [
            "按支付方式聚合报错日志与失败率",
            "复现各方式的失败路径（证书/配置/回调）",
            "逐项修复并加兜底提示",
            "回归验证各支付方式可用",
        ],
        "success_metrics": ["各支付方式失败率下降", "移动支付成功率提升", "相关投诉 7 天内下降"],
        "expected_impact": "恢复移动支付可用性，减少投诉",
    },
    PrimaryCategory.CHECKOUT_STUCK: {
        "title": "修复收银台卡住/无限加载",
        "summary": "收银台卡住、冻结或无限加载，用户无法完成支付。",
        "recommendation": "排查收银台前端状态机与接口挂起，定位卡死路径。",
        "action_items": [
            "收集卡死页面的截图/日志/版本分布",
            "复现卡死路径（加载/提交/回调）",
            "修复状态机并加超时兜底与重试",
            "回归验证收银台流程可完成",
        ],
        "success_metrics": ["收银台卡死率下降", "收银台完成率提升", "卡住类投诉 7 天内下降"],
        "expected_impact": "恢复收银台可用性，减少卡单",
    },
    PrimaryCategory.CHECKOUT_CRASH: {
        "title": "修复收银台崩溃",
        "summary": "应用在支付/收银台上下文崩溃，直接中断下单。",
        "recommendation": "聚合崩溃堆栈，定位收银台崩溃的代码路径。",
        "action_items": [
            "聚合崩溃日志按版本/机型分布",
            "定位崩溃堆栈对应的代码路径",
            "修复并加崩溃兜底/降级",
            "灰度验证崩溃率下降",
        ],
        "success_metrics": ["收银台崩溃率下降", "崩溃前会话恢复率提升", "崩溃类投诉 7 天内下降"],
        "expected_impact": "消除崩溃中断，恢复下单链路",
    },
    PrimaryCategory.CHECKOUT_PERFORMANCE: {
        "title": "优化收银台加载速度",
        "summary": "收银台加载缓慢但最终能完成，影响体验。",
        "recommendation": "分析收银台加载耗时，定位慢资源与接口。",
        "action_items": [
            "测量收银台各阶段加载耗时分布",
            "定位慢接口/慢资源并优化",
            "加骨架屏/预加载改善感知",
            "灰度验证加载耗时下降",
        ],
        "success_metrics": ["收银台加载耗时下降", "加载完成率提升", "体验类反馈下降"],
        "expected_impact": "提升支付体验，减少中途流失",
    },
    PrimaryCategory.DUPLICATE_CHARGE: {
        "title": "消除重复扣费",
        "summary": "同一订单被重复扣费，属资金安全问题，需优先处理。",
        "recommendation": "排查支付回调/幂等，定位重复扣费的触发路径并加幂等保护。",
        "action_items": [
            "核对重复扣费订单的支付流水与回调",
            "定位缺幂等的触发路径",
            "加幂等键并修复重复扣费，已扣款自动退款",
            "回归验证同一订单只扣一次",
        ],
        "success_metrics": ["重复扣费率归零", "自动退款及时率", "相关投诉 7 天内归零"],
        "expected_impact": "消除资金风险，避免信任与退款成本",
    },
    PrimaryCategory.INCORRECT_CHARGE: {
        "title": "修正扣费金额/项目不符",
        "summary": "扣费金额或项目与用户预期不符（错误金额/未订阅被扣费）。",
        "recommendation": "核对计费逻辑与订单明细，定位错扣/误扣的触发条件。",
        "action_items": [
            "核对错扣订单的计费明细与用户账户状态",
            "定位计费规则漏洞（续订/套餐判定）",
            "修正计费并批量退款受影响用户",
            "加计费对账监控防止复发",
        ],
        "success_metrics": ["错扣发生率下降", "计费对账差异归零", "相关投诉 7 天内下降"],
        "expected_impact": "消除错扣，挽回信任与退款成本",
    },
}


def _classify(text: str) -> tuple[PrimaryCategory, Severity, IssueType]:
    """关键词匹配 → (category, severity, issue_type)；未命中默认 payment_failed。"""
    for keywords, category, severity, issue_type in _CLASSIFY_RULES:
        if any(k in text for k in keywords):
            return category, severity, issue_type
    return PrimaryCategory.PAYMENT_FAILED, Severity.HIGH, IssueType.PROBLEM


def _entities(text: str) -> list[str]:
    ents = []
    for marker, name in (("apple pay", "Apple Pay"), ("google pay", "Google Pay"), ("paypal", "PayPal"), ("crypto", "Crypto")):
        if marker in text:
            ents.append(name)
    return ents or ["Payment"]


class FakeLLM(LLMClient):
    """确定性假 LLM：不调用真实模型，输出"基于输入关键词接地"的合法结构化结果。

    与旧版（固定返回同一句）的区别：现在会从输入文本推导分类/命名/建议，
    让无 API key 的 demo 也能看到有区分度、可执行、不重复的输出。
    """

    def complete(self, messages, output_schema):
        text = _user_text(messages)
        if output_schema is FeedbackAnalysis:
            category, severity, issue_type = _classify(text)
            return FeedbackAnalysis(
                summary=_SUMMARY[category],
                primary_category=category,
                issue_type=issue_type,
                severity=severity,
                entities=_entities(text),
                confidence=0.9,
                needs_review=False,
            )
        if output_schema is ClusterNaming:
            category, _, _ = _classify(text)
            return ClusterNaming(title=_CLUSTER_TITLE[category], description=_CLUSTER_DESC[category])
        if output_schema is ProductOpportunity:
            category, _, _ = _classify(text)
            opp = _OPPORTUNITY.get(category, _OPPORTUNITY[PrimaryCategory.PAYMENT_FAILED])
            return ProductOpportunity(confidence=0.9, **opp)
        raise NotImplementedError(
            f"FakeLLM 尚未支持 schema {getattr(output_schema, '__name__', output_schema)}"
        )


class NullLLM(LLMClient):
    """空 LLM：调用即报错，防止在接入真实 provider 前被误用。"""

    def complete(self, messages, output_schema):
        raise NotImplementedError(
            "NullLLM 不会生成输出；请配置真实 provider，或在测试中使用 FakeLLM"
        )


class DeepSeekProvider(LLMClient):
    """真实 DeepSeek LLM（OpenAI 兼容 API）。

    结构化输出：JSON 模式 + Pydantic schema 校验。
    - JSON 解析失败 / schema 校验失败 → 抛 LLMOutputError（绝不静默转成合法数据）。
    - API / 网络 / 鉴权错误 → 抛 LLMProviderError。
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.0,
    ) -> None:
        if not api_key:
            raise LLMProviderError("DEEPSEEK_API_KEY 未设置")
        from openai import OpenAI  # 惰性导入，测试环境不加载

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature
        # 可观测性：累计本次会话的 token / 延迟 / 调用次数
        self.total_tokens = 0
        self.total_calls = 0
        self.total_latency_ms = 0.0

    def complete(self, messages, output_schema):
        from pydantic import ValidationError

        started = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=self._temperature,
            )
        except Exception as exc:
            raise LLMProviderError(f"DeepSeek API 调用失败：{exc}") from exc

        self.total_latency_ms += (time.perf_counter() - started) * 1000
        self.total_calls += 1
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.total_tokens += int(getattr(usage, "total_tokens", 0) or 0)

        content = (resp.choices[0].message.content or "").strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMOutputError(f"LLM 返回了无法解析的 JSON：{content[:200]!r}") from exc

        try:
            return output_schema.model_validate(data)
        except ValidationError as exc:
            raise LLMOutputError(f"LLM 输出不符合 schema：{exc}") from exc


def get_llm() -> LLMClient:
    """根据配置返回 LLM 客户端：有 DEEPSEEK_API_KEY 用 DeepSeek，否则回退 FakeLLM。"""
    from app.core.config import settings

    if settings.deepseek_api_key:
        return DeepSeekProvider(settings.deepseek_api_key, model=settings.deepseek_model)
    return FakeLLM()
