"""Standart foydalanuvchini yaratish (oddiy auth uchun).

Login ma'lumotlari .env'dagi SUPER_ADMIN_* qiymatlaridan olinadi
(qattiq yozilmagan). Bir necha marta ishlatish xavfsiz — bor bo'lsa o'tkazadi.

Ishga tushirish:
    python -m scripts.seed_user
    # docker: docker compose ... exec app python -m scripts.seed_user
"""
import asyncio

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.utils.security import hash_password
from src.main.config import config
from src.user.enums import UserRole
from src.user.models import User

engine = create_async_engine(config.postgres.dsn_async)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def seed_user() -> None:
    username = config.administration.SUPER_ADMIN_USERNAME
    email = config.administration.SUPER_ADMIN_EMAIL

    async with async_session() as session:
        stmt = select(User).where(
            or_(User.username == username, User.email == email)
        )
        if (await session.execute(stmt)).scalar_one_or_none():
            print(f"Foydalanuvchi '{username}' allaqachon bor — o'tkazildi.")
            return

        user = User(
            first_name="Turon",
            last_name="Admin",
            email=email,
            username=username,
            phone_number=config.administration.SUPER_ADMIN_PHONE,
            password_hash=hash_password(config.administration.SUPER_ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_verified=True,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Foydalanuvchi '{username}' yaratildi.")


if __name__ == "__main__":
    asyncio.run(seed_user())
