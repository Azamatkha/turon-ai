"""add translate_lang to chat_sessions

Revision ID: f4c2a8d19b37
Revises: e3b9c2a71f08
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f4c2a8d19b37"
down_revision: Union[str, None] = "e3b9c2a71f08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tarjimon rejimi: NULL — o'chiq, "pending" — til kutilmoqda,
    # "en" / "ru" / "uz" / "uz_cyrl" — tanlangan til.
    op.add_column(
        "chat_sessions",
        sa.Column("translate_lang", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "translate_lang")
