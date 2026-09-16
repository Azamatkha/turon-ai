"""username unikalligi registrsiz (lower(username) bo'yicha)

Revision ID: d1f7b3c48a60
Revises: c9a4e1b70d52
Create Date: 2026-09-16 12:00:00.000000

Login endi foydalanuvchi yozganidek saqlanadi ("turonAI"). Shuning uchun
unikal indeks ustunning o'ziga emas, `lower(username)` ga qo'yiladi — aks
holda "turonAI" va "turonai" ikki xil hisoblanib, ikkita akkaunt ochilardi.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d1f7b3c48a60"
down_revision: Union[str, None] = "c9a4e1b70d52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_users_username_not_deleted", table_name="users")
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_users_username_not_deleted "
            "ON users (lower(username)) WHERE is_deleted = false"
        )
    )


def downgrade() -> None:
    op.drop_index("uq_users_username_not_deleted", table_name="users")
    op.create_index(
        "uq_users_username_not_deleted",
        "users",
        ["username"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
