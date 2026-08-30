"""SQLAlchemy 声明式基类。

决策：使用 SQLAlchemy 2.0 的 DeclarativeBase（现代声明式风格）。
所有 ORM 模型继承自这里的 `Base`，其 metadata 供 Alembic 自动生成迁移。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
