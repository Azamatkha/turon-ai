"""ghost stamp — bazada bu revisiyaga stamp qo'yilgan, lekin asl fayli yo'qolgan.
Bo'sh (no-op) migratsiya sifatida tiklanmoqda, shunda alembic zanjiri uzilmaydi.

Revision ID: a693ada90326
Revises: 64c95b9291a9
Create Date: 2026-07-14 00:00:00.000001

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "a693ada90326"
down_revision: Union[str, None] = "64c95b9291a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
