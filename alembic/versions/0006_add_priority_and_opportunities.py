"""add priority_score and product_opportunities table

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-30

Phase 5：给 product_problems 加 priority_score；新增 product_opportunities 表。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_problems",
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_table(
        "product_opportunities",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_problem_id", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_opportunities_problem", "product_opportunities", ["product_problem_id"])


def downgrade() -> None:
    op.drop_index("ix_product_opportunities_problem", table_name="product_opportunities")
    op.drop_table("product_opportunities")
    op.drop_column("product_problems", "priority_score")
