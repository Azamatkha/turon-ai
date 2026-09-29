"""add completion_tokens and finish_reason to chat_messages

Revision ID: b8e2f6a4d913
Revises: a7d3e5f1c294
Create Date: 2026-09-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b8e2f6a4d913"
down_revision: Union[str, None] = "a7d3e5f1c294"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Assistant javobining token statistikasi — sahifa yangilanganda ham
    # token hisoblagichi ko'rinib turishi uchun. Eski yozuvlarda NULL.
    op.add_column(
        "chat_messages",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("finish_reason", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "finish_reason")
    op.drop_column("chat_messages", "completion_tokens")
