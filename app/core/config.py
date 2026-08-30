"""应用配置。

决策：使用 pydantic-settings，将配置集中在单个 `Settings` 对象中，
通过模块级 `settings` 单例访问；密钥与可替换项（数据库、LLM provider）
都来自环境变量 / .env，绝不写入代码。

备选方案：
- 手写 os.environ 读取：零依赖，但缺类型与默认值，易出错。
- 多个零散 config 模块：分散，不利于评审。

权衡：pydantic-settings 是一个小型依赖，换来类型安全、默认值、
`.env` 加载与校验能力。

为什么选它：这是 FastAPI 生态的标准做法，且"配置可替换"是本项目的核心目标。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局应用配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未知环境变量，避免误触发
    )

    # 应用
    app_name: str = "AI Product Feedback Agent"
    environment: str = "development"
    log_level: str = "INFO"

    # 数据库（默认 SQLite；切换 Postgres 只需改 DATABASE_URL）
    database_url: str = "sqlite:///./data/app.db"

    # LLM Provider（默认 mock；接入 DeepSeek 见 services/llm.py）
    llm_provider: str = "mock"
    llm_model: str = "fake"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"

    # Tracing（当前 memory / null；后续可替换，见 core/tracing.py）
    tracer_backend: str = "memory"

    # Embedding 与聚类（Phase 4）
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    clustering_threshold: float = 0.75


@lru_cache
def get_settings() -> Settings:
    """返回缓存的 Settings 单例（进程内只创建一次）。"""
    return Settings()


settings = get_settings()
