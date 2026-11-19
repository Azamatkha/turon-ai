"""add kb_categories (admin boshqaradigan bilim bazasi turkumlari)

Revision ID: d3a8b6c2e517
Revises: c9e2f7a4d613
Create Date: 2026-11-19 00:00:00.000000

"""

from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d3a8b6c2e517"
down_revision: Union[str, None] = "c9e2f7a4d613"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Avvalgi 6 ta qat'iy turkum — o'z kalitlari bilan. Shunda admin oldin
# qo'lda qo'ygan turkumlar (payload'da "credit", "deposit", ...) ko'chirishsiz
# ishlayveradi. Kalit so'zlar — ilgari kodda turgan ro'yxat.
_SEED = [
    ("card", "Bank kartalari", "karta", 10),
    ("credit", "Kreditlar", "kredit, ipoteka, qarz, mikroqarz, mikrokredit", 20),
    ("deposit", "Omonatlar", "omonat, depozit", 30),
    ("transfer", "Pul o'tkazmalari", "o'tkazma, otkazma, o'tkazish, otkazish", 40),
    (
        "branch",
        "Filiallar (bank xizmatlari markazlari va ofislari)",
        "filial, bxm, bank xizmatlari markazi, bank xizmatlari ofisi",
        50,
    ),
    ("other", "Boshqa xizmatlar", "", 60),
]


def upgrade() -> None:
    table = op.create_table(
        "kb_categories",
        sa.Column("key", sa.String(length=40), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        table,
        [
            {
                "key": key,
                "name": name,
                "keywords": keywords,
                "sort_order": order,
                "created_at": now,
                "updated_at": now,
            }
            for key, name, keywords, order in _SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("kb_categories")
