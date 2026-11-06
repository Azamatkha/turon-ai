"""users: keywords — admin qo'yadigan kalit so'zlar (xodim nimaga mas'ul)

Masalan "edo", "ip telefoniya". Chat-bot "EDO ga kim qaraydi?" savolida
shu kalit so'zli xodimni topadi.

Revision ID: a8d4e1c7b352
Revises: f3b9d2e6a417
Create Date: 2026-11-06 11:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8d4e1c7b352"
down_revision: Union[str, None] = "f3b9d2e6a417"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("keywords", postgresql.ARRAY(sa.String(length=50)), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "keywords")
