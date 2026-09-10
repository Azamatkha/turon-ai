"""add user verification fields (face-id + xodimlar bazasi)

Revision ID: b3d8f1a6c2e9
Revises: e7c2b9d43f18
Create Date: 2026-09-10 00:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b3d8f1a6c2e9"
down_revision: Union[str, None] = "e7c2b9d43f18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Hammasi nullable — mavjud userlarga tegmaydi (ular is_verified=true qoladi)
    op.add_column("users", sa.Column("pnfl", sa.String(length=14), nullable=True))
    op.add_column("users", sa.Column("patronym", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("doc_seria", sa.String(length=10), nullable=True))
    op.add_column("users", sa.Column("doc_number", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(length=150), nullable=True))
    op.add_column("users", sa.Column("branch", sa.String(length=150), nullable=True))
    op.create_index(
        "uq_users_pnfl_not_deleted",
        "users",
        ["pnfl"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false AND pnfl IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_pnfl_not_deleted", table_name="users")
    op.drop_column("users", "branch")
    op.drop_column("users", "position")
    op.drop_column("users", "birth_date")
    op.drop_column("users", "doc_number")
    op.drop_column("users", "doc_seria")
    op.drop_column("users", "patronym")
    op.drop_column("users", "pnfl")
