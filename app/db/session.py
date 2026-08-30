"""数据库连接与会话。

决策：使用 SQLAlchemy 2.0 的 engine + sessionmaker，默认 SQLite（零配置），
通过 DATABASE_URL 可切换到 Postgres（只需改配置，代码不变）。

SQLite 特有参数 check_same_thread=False：FastAPI 多线程下允许跨线程复用连接。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI 依赖：提供一个数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
