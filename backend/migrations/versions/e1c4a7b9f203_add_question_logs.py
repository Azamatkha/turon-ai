"""add question_logs

Revision ID: e1c4a7b9f203
Revises: d8b3f2c6a915
Create Date: 2026-11-09 00:00:02.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e1c4a7b9f203"
down_revision: Union[str, None] = "d8b3f2c6a915"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Botga berilgan savollar — TOP va javobsiz savollar tahlili uchun
    op.create_table(
        "question_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("normalized", sa.String(length=300), nullable=False),
        sa.Column("intent", sa.String(length=30), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("top_score", sa.Float(), nullable=True),
        sa.Column("sources_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_question_logs_user_id", "question_logs", ["user_id"])
    op.create_index("ix_question_logs_normalized", "question_logs", ["normalized"])
    op.create_index("ix_question_logs_outcome", "question_logs", ["outcome"])
    op.create_index("ix_question_logs_created_at", "question_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_question_logs_created_at", table_name="question_logs")
    op.drop_index("ix_question_logs_outcome", table_name="question_logs")
    op.drop_index("ix_question_logs_normalized", table_name="question_logs")
    op.drop_index("ix_question_logs_user_id", table_name="question_logs")
    op.drop_table("question_logs")
