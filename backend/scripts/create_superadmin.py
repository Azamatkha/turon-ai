import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.utils.security import hash_password
from src.main.config import config
from src.user.enums import UserRole
from src.user.models import User

engine = create_async_engine(config.postgres.dsn_async)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def create_superadmin() -> None:
    async with async_session() as session:
        stmt = select(User).where(User.role == UserRole.ADMIN).limit(1)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            print("Admin already exists, skipping.")
            return

        admin = User(
            first_name="Super",
            last_name="Admin",
            email=config.administration.SUPER_ADMIN_EMAIL,
            username=config.administration.SUPER_ADMIN_USERNAME,
            phone_number=config.administration.SUPER_ADMIN_PHONE,
            password_hash=hash_password(config.administration.SUPER_ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_verified=True,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"Superadmin '{admin.username}' created.")


if __name__ == "__main__":
    asyncio.run(create_superadmin())
