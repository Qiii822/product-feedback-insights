"""add cohesion_score and needs_review to product_problems

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-30

Phase 4 review：新增 cohesion_score（簇内语义一致度）与 needs_review
（区分 confirmed / candidate），并把 confidence 改为 provisional 占位。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_problems",
        sa.Column("cohesion_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "product_problems",
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("product_problems", "needs_review")
    op.drop_column("product_problems", "cohesion_score")
