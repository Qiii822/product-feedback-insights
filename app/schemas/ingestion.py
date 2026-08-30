"""摄取结果（IngestionResult）数据契约。"""

from pydantic import BaseModel, Field


class IngestionResult(BaseModel):
    """一次摄取操作的统计结果。"""

    total_rows: int = 0  # 输入总行数
    added: int = 0  # 实际新增
    skipped_duplicates: int = 0  # 精确重复被跳过
    invalid: int = 0  # 校验失败（缺失必填字段等）
    errors: list[str] = Field(default_factory=list)  # 致命失败明细
    warnings: list[str] = Field(default_factory=list)  # 非致命警告（如 rating 无效）
