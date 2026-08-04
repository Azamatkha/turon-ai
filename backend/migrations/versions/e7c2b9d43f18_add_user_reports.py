"""add user reports

Revision ID: e7c2b9d43f18
Revises: d4f1a2c9e7b3
Create Date: 2026-08-04 00:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e7c2b9d43f18"
down_revision: Union[str, None] = "d4f1a2c9e7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("screenshot_path", sa.String(length=255), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="new"
        ),
        sa.Column("admin_comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_reports_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_reports")),
    )
    op.create_index(
        op.f("ix_user_reports_user_id"), "user_reports", ["user_id"]
    )
    op.create_index(op.f("ix_user_reports_status"), "user_reports", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_user_reports_status"), table_name="user_reports")
    op.drop_index(op.f("ix_user_reports_user_id"), table_name="user_reports")
    op.drop_table("user_reports")
