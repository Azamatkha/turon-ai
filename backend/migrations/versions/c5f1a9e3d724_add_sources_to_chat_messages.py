"""add sources to chat_messages

Revision ID: c5f1a9e3d724
Revises: a8d4e1c7b352
Create Date: 2026-11-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c5f1a9e3d724"
down_revision: Union[str, None] = "a8d4e1c7b352"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Assistant javobi tayangan hujjatlar (manba chiplari). Eski yozuvlarda NULL.
    op.add_column(
        "chat_messages",
        sa.Column("sources", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "sources")
