"""add product_problems and evidence tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-30

Phase 4：新增产品问题（product_problems）与证据（evidence）两张表。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_problems",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("affected_segments", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_problem_id", sa.String(length=32), nullable=True),
        sa.Column("feedback_item_id", sa.String(length=32), nullable=True),
        sa.Column("analysis_id", sa.String(length=32), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_product_problem_id", "evidence", ["product_problem_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_product_problem_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_table("product_problems")
