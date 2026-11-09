"""add vote_reason, vote_comment, vote_reviewed to chat_messages

Revision ID: d8b3f2c6a915
Revises: c5f1a9e3d724
Create Date: 2026-11-09 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d8b3f2c6a915"
down_revision: Union[str, None] = "c5f1a9e3d724"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dislike sababi va izohi + admin ko'rib chiqqanmi
    op.add_column(
        "chat_messages",
        sa.Column("vote_reason", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("vote_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "vote_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Admin navbati: vote='down' va ko'rib chiqilmaganlar tez topilsin
    op.create_index(
        "ix_chat_messages_vote_down",
        "chat_messages",
        ["vote", "vote_reviewed", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_vote_down", table_name="chat_messages")
    op.drop_column("chat_messages", "vote_reviewed")
    op.drop_column("chat_messages", "vote_comment")
    op.drop_column("chat_messages", "vote_reason")
