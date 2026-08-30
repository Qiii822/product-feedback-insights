"""日志配置。

决策：使用 Python 标准库 `logging`，不做结构化日志框架。

备选方案：
- structlog / loguru：提供结构化 JSON 日志，便于后续接入 tracing 平台。
- 标准库 logging：零额外依赖，功能足够。

权衡：structlog 为未来"结构化日志 → tracing"预留了更好的基础，但当前
pipeline 尚未产生需要结构化分析的日志，提前引入属于"为未来而加"的复杂度。

为什么选标准库：Phase 1 无明确结构化日志需求；标准库零依赖、够用。
当 tracing 真正需要结构化日志时（Phase 6+），可低成本迁移到 structlog。
"""

import logging
import sys

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    """初始化根 logger（幂等：重复调用不会叠加 handler）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.addHandler(handler)
    _CONFIGURED = True
