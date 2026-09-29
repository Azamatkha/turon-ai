"""add face_id_signature_logs

Revision ID: a7d3e5f1c294
Revises: f4c2a8d19b37
Create Date: 2026-09-29 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7d3e5f1c294"
down_revision: Union[str, None] = "f4c2a8d19b37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "face_id_signature_logs",
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column(
            "claims", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("result", sa.String(length=255), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_face_id_signature_logs_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_face_id_signature_logs")),
    )
    op.create_index(
        op.f("ix_face_id_signature_logs_user_id"),
        "face_id_signature_logs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_face_id_signature_logs_user_id"),
        table_name="face_id_signature_logs",
    )
    op.drop_table("face_id_signature_logs")
