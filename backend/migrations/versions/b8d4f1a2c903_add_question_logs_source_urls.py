"""add question_logs.source_urls (veb-qidiruv manbalari)

Revision ID: b8d4f1a2c903
Revises: a7c3e9d2b514
Create Date: 2026-11-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8d4f1a2c903"
down_revision: Union[str, None] = "a7c3e9d2b514"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "question_logs",
        sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("question_logs", "source_urls")
