"""initial users table

Revision ID: 0001_initial_users
Revises:
Create Date: 2026-06-23

Turon AI uchun boshlang'ich migratsiya: `users` jadvali (oddiy auth uchun).
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_users"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=50), nullable=False),
        sa.Column("last_name", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=60), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            # SQLAlchemy SQLEnum(UserRole) enum NOMLARINI saqlaydi (ADMIN/MODERATOR/USER)
            "role",
            sa.Enum("ADMIN", "MODERATOR", "USER", name="userrole"),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])
    op.create_index(
        "uq_users_email_active_not_deleted",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "uq_users_username_not_deleted",
        "users",
        ["username"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_username_not_deleted", table_name="users")
    op.drop_index("uq_users_email_active_not_deleted", table_name="users")
    op.drop_index("ix_users_is_deleted", table_name="users")
    op.drop_table("users")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
