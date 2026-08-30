"""recreate feedback_items with Phase 2 fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-30

Phase 2 将 FeedbackItem 从"自由 metadata dict"改为固定字段，
数据模型变化较大。Phase 1 表无数据，故采用 drop + recreate；
生产环境若已有数据，应使用 ALTER 并编写数据迁移脚本。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("feedback_items")
    op.create_table(
        "feedback_items",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("feedback_id", sa.String(length=100), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("platform", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("app_version", sa.String(length=50), nullable=True),
        sa.Column("customer_segment", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("feedback_items")
    op.create_table(
        "feedback_items",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
