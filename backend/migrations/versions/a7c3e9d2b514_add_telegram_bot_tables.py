"""add telegram_bot_users and telegram_bot_messages

Revision ID: a7c3e9d2b514
Revises: f2d5b8c1e406
Create Date: 2026-11-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7c3e9d2b514"
down_revision: Union[str, None] = "f2d5b8c1e406"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    # Telegram yordam boti (aihelp) userlari — bot o'zi push qiladi
    op.create_table(
        "telegram_bot_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "full_name", sa.String(length=256), nullable=False, server_default=""
        ),
        sa.Column("language", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("reg_step", sa.String(length=8), nullable=False, server_default=""),
        sa.Column(
            "is_banned", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("telegram_id", name="uq_telegram_bot_users_telegram_id"),
    )
    op.create_index(
        "ix_telegram_bot_users_last_message_at",
        "telegram_bot_users",
        ["last_message_at"],
    )

    # Murojaatlar va admin javoblari
    op.create_table(
        "telegram_bot_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bot_message_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("telegram_bot_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("items", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "admin_name", sa.String(length=128), nullable=False, server_default=""
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint(
            "bot_message_id", name="uq_telegram_bot_messages_bot_message_id"
        ),
    )
    op.create_index(
        "ix_telegram_bot_messages_user_id", "telegram_bot_messages", ["user_id"]
    )
    op.create_index(
        "ix_telegram_bot_messages_sent_at", "telegram_bot_messages", ["sent_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_telegram_bot_messages_sent_at", table_name="telegram_bot_messages"
    )
    op.drop_index(
        "ix_telegram_bot_messages_user_id", table_name="telegram_bot_messages"
    )
    op.drop_table("telegram_bot_messages")
    op.drop_index(
        "ix_telegram_bot_users_last_message_at", table_name="telegram_bot_users"
    )
    op.drop_table("telegram_bot_users")
