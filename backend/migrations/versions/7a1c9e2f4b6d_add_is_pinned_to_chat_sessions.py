"""add is_pinned to chat_sessions

Revision ID: 7a1c9e2f4b6d
Revises: a693ada90326
Create Date: 2026-07-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7a1c9e2f4b6d"
down_revision: Union[str, None] = "a693ada90326"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "is_pinned")
