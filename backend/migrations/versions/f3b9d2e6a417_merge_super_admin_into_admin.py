"""users: super_admin roli bekor qilindi — hamma yana bitta `admin` rolida

e1a7c4b9d250 da admin ikkiga bo'lingan edi (super_admin / admin). Qaror
o'zgardi: bitta umumiy admin roli qoladi. Kodda SUPER_ADMIN endi yo'q,
shuning uchun bazadagi SUPER_ADMIN yozuvlari ADMIN ga qaytariladi — aks holda
SQLAlchemy noma'lum enum qiymatini o'qiyolmay xato berardi.

Enum turidagi 'SUPER_ADMIN' qiymatining o'zi bazada qoladi (Postgres
enum'dan qiymat o'chirmaydi), lekin hech bir yozuv uni ishlatmaydi.

Revision ID: f3b9d2e6a417
Revises: e1a7c4b9d250
Create Date: 2026-11-06 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f3b9d2e6a417"
down_revision: Union[str, None] = "e1a7c4b9d250"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'SUPER_ADMIN'")


def downgrade() -> None:
    # Kim avval super admin bo'lganini bilib bo'lmaydi — qaytarish yo'q
    pass
