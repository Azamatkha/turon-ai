"""users: link to the Turon ID account (SSO)

Revision ID: c3d9a1f2e7b4
Revises: b8e2f6a4d913
Create Date: 2026-10-15 19:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d9a1f2e7b4"
down_revision: Union[str, None] = "b8e2f6a4d913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("turon_id_sub", sa.UUID(), nullable=True))
    op.create_index(
        "uq_users_turon_id_sub_not_deleted",
        "users",
        ["turon_id_sub"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false AND turon_id_sub IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_turon_id_sub_not_deleted", table_name="users")
    op.drop_column("users", "turon_id_sub")
