"""make source/platform/customer_segment nullable (missing vs unknown)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-30

D8.3：区分"字段未提供（None）"与"提供了但无法映射（unknown）"，
因此这三列需要允许 NULL，不再有 NOT NULL + server_default="unknown"。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("feedback_items") as batch_op:
        batch_op.alter_column("source", nullable=True, server_default=None)
        batch_op.alter_column("platform", nullable=True, server_default=None)
        batch_op.alter_column("customer_segment", nullable=True, server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("feedback_items") as batch_op:
        batch_op.alter_column("source", nullable=False, server_default="unknown")
        batch_op.alter_column("platform", nullable=False, server_default="unknown")
        batch_op.alter_column("customer_segment", nullable=False, server_default="unknown")
