"""add opportunity action_items and success_metrics

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-23

给 product_opportunities 加 action_items / success_metrics（JSON，可空），
让产品机会输出可执行的修复步骤与验证指标。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_opportunities",
        sa.Column("action_items", sa.JSON(), nullable=True),
    )
    op.add_column(
        "product_opportunities",
        sa.Column("success_metrics", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_opportunities", "success_metrics")
    op.drop_column("product_opportunities", "action_items")
