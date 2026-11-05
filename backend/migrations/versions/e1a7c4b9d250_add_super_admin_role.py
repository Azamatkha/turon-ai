"""users: super_admin roli; mavjud adminlar super admin bo'ladi

Ilgari bitta `admin` roli hamma narsaga ruxsat berardi. Endi:
  * super_admin — to'liq boshqaruv (rollar, bilim bazasi, sozlamalar);
  * admin — boshqaruv paneli, foydalanuvchilar va murojaatlarni faqat ko'radi.

Hozirgi barcha ADMIN'lar SUPER_ADMIN ga o'tkaziladi — aks holda deploy'dan
keyin hech kim rol almashtira olmay qolardi. Kimni oddiy admin qilish
kerakligini super admin keyin panelda o'zi belgilaydi.

Revision ID: e1a7c4b9d250
Revises: a5e8c1d2f9b7
Create Date: 2026-11-04 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e1a7c4b9d250"
down_revision: Union[str, None] = "a5e8c1d2f9b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum'ga qo'shilgan yangi qiymatni o'sha tranzaksiyaning o'zida ishlatib
    # bo'lmaydi (Postgres cheklovi) — shuning uchun alohida commit qilinadi.
    # SQLAlchemy Enum'i bazada a'zo NOMINI saqlaydi ("ADMIN"), qiymatini emas.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPER_ADMIN'")
    op.execute("UPDATE users SET role = 'SUPER_ADMIN' WHERE role = 'ADMIN'")


def downgrade() -> None:
    # Postgres enum'dan qiymatni o'chirib bo'lmaydi — faqat rollarni qaytaramiz
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'SUPER_ADMIN'")
