"""add users.ip_number (bank ichki telefon raqami)

Revision ID: e3b9c2a71f08
Revises: d1f7b3c48a60
Create Date: 2026-09-21 00:00:00.000000

Kontaktlar ikkita alohida ustunda turadi: `phone_number` (mobil, +998...)
avvaldan bor edi, `ip_number` (1-4 xonali ichki raqam) yangi. Ikkalasi ham
ixtiyoriy — foydalanuvchi o'zi yoki admin kiritadi.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e3b9c2a71f08"
down_revision: Union[str, None] = "d1f7b3c48a60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ip_number", sa.String(length=4), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ip_number")
