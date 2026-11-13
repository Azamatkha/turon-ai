"""add answer and verdict to question_logs

Revision ID: c9e2f7a4d613
Revises: b8d4f1a2c903
Create Date: 2026-11-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c9e2f7a4d613"
down_revision: Union[str, None] = "b8d4f1a2c903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bot bergan javob — admin "Savollar tahlili"da savol yonida ko'radi.
    # Eski yozuvlarda NULL.
    op.add_column("question_logs", sa.Column("answer", sa.Text(), nullable=True))
    # Javob tekshiruvi natijasi: ok | fixed | failed | unchecked (NULL — tekshirilmaydigan)
    op.add_column(
        "question_logs", sa.Column("verdict", sa.String(length=20), nullable=True)
    )
    # Tekshiruvchi topgan kamchilik (rad etilgan bo'lsa)
    op.add_column("question_logs", sa.Column("verdict_note", sa.Text(), nullable=True))
    op.create_index("ix_question_logs_verdict", "question_logs", ["verdict"])


def downgrade() -> None:
    op.drop_index("ix_question_logs_verdict", table_name="question_logs")
    op.drop_column("question_logs", "verdict_note")
    op.drop_column("question_logs", "verdict")
    op.drop_column("question_logs", "answer")
