"""FeedbackAnalyzer（反馈理解）测试。"""

import pytest

from app.prompts.analysis import SYSTEM_PROMPT
from app.schemas.analysis import FeedbackAnalysis
from app.schemas.enums import IssueType, PrimaryCategory
from app.schemas.feedback import FeedbackItem
from app.services.analyzer import LLMFeedbackAnalyzer
from app.services.llm import FakeLLM


def test_analyzer_produces_linked_analysis():
    analyzer = LLMFeedbackAnalyzer(FakeLLM(), model="fake", prompt_version="v1")
    item = FeedbackItem(feedback_id="fb_1", raw_text="Payment failed again.")
    result = analyzer.analyze(item)
    assert isinstance(result, FeedbackAnalysis)
    assert result.feedback_item_id == item.id
    assert result.model == "fake"
    assert result.prompt_version == "v1"
    assert result.primary_category is PrimaryCategory.PAYMENT_FAILED
    assert result.issue_type is IssueType.PROBLEM
    assert result.summary.strip()


class _EmptySummaryLLM(FakeLLM):
    def complete(self, messages, output_schema):
        out = super().complete(messages, output_schema)
        return out.model_copy(update={"summary": "   "})


def test_analyzer_rejects_empty_summary():
    # 系统绝不静默接受非法输出（空 summary）
    analyzer = LLMFeedbackAnalyzer(_EmptySummaryLLM())
    item = FeedbackItem(feedback_id="fb_1", raw_text="x")
    with pytest.raises(ValueError):
        analyzer.analyze(item)


def test_prompt_lists_all_categories_and_issue_types():
    # 守护 prompt 与枚举词表的一致性，防止漂移
    for c in PrimaryCategory:
        assert c.value in SYSTEM_PROMPT
    for i in IssueType:
        assert i.value in SYSTEM_PROMPT
