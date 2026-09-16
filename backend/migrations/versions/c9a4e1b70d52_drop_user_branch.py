"""drop users.branch (departament/filial bitta maydonda)

Revision ID: c9a4e1b70d52
Revises: b3d8f1a6c2e9
Create Date: 2026-09-16 00:00:00.000000

Xodimlar bazasi (EDO) bitta `depart` maydonini qaytaradi va unda goh
departament ("Axborot texnologiyalari departamenti"), goh filial
("Navoiy BXM") keladi. Ikkita alohida ustun saqlashning ma'nosi yo'q:
`branch` olib tashlanadi, hammasi `department` da turadi.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c9a4e1b70d52"
down_revision: Union[str, None] = "b3d8f1a6c2e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ustun o'chishidan oldin ma'lumot yo'qolmasin: bo'lim bo'sh (yoki standart
    # "Boshqa") bo'lgan userlarda filial nomi bo'lim sifatida qoladi.
    op.execute(
        sa.text(
            "UPDATE users SET department = branch "
            "WHERE branch IS NOT NULL AND branch <> '' "
            "AND (department IS NULL OR department = '' OR department = 'Boshqa')"
        )
    )
    op.drop_column("users", "branch")


def downgrade() -> None:
    op.add_column("users", sa.Column("branch", sa.String(length=150), nullable=True))
