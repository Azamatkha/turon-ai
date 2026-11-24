"""add tools to question_logs

Revision ID: f7b2d9e4a581
Revises: e5a1c8f3b072
Create Date: 2026-11-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f7b2d9e4a581"
down_revision: Union[str, None] = "e5a1c8f3b072"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tool-calling agenti chaqirgan asboblar (tartib bilan) — admin "Savollar
    # tahlili"da javob qaysi asboblar bilan tuzilganini ko'radi. Eski
    # yozuvlarda va agent ishlamagan javoblarda NULL.
    op.add_column(
        "question_logs",
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("question_logs", "tools")
