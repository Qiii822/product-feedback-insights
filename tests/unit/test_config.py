"""配置模块测试。

使用 `_env_file=None` 关闭 .env 读取，保证测试确定性、不受本地环境影响。
"""

from app.core.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.environment == "development"
    assert s.log_level == "INFO"
    assert s.llm_provider == "mock"


def test_database_url_default_is_sqlite():
    s = Settings(_env_file=None)
    assert s.database_url.startswith("sqlite:///")


def test_deepseek_api_key_default_to_none(monkeypatch):
    # 关键点：pydantic-settings 会读取真实环境变量（不只是 .env 文件），
    # 因此必须显式清除相关环境变量，才能测试"未设置时的默认值"。
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    s = Settings(_env_file=None)
    assert s.deepseek_api_key is None
