"""Reset the password of an existing admin user.

Usage (inside the app container):
    python -m scripts.reset_admin_password              # uses SUPER_ADMIN_PASSWORD from .env
    python -m scripts.reset_admin_password "NewPass123!"  # explicit password
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.utils.security import hash_password
from src.main.config import config
from src.user.enums import UserRole
from src.user.models import User

engine = create_async_engine(config.postgres.dsn_async)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def reset_admin_password(new_password: str) -> None:
    async with async_session() as session:
        stmt = (
            select(User)
            .where(User.username == config.administration.SUPER_ADMIN_USERNAME)
            .limit(1)
        )
        admin = (await session.execute(stmt)).scalar_one_or_none()

        if admin is None:
            stmt = select(User).where(User.role == UserRole.ADMIN).limit(1)
            admin = (await session.execute(stmt)).scalar_one_or_none()

        if admin is None:
            print("No admin user found. Run scripts.create_superadmin first.")
            return

        admin.password_hash = hash_password(new_password)
        admin.is_active = True
        admin.is_verified = True
        await session.commit()
        print(f"Password reset for admin '{admin.username}' ({admin.email}).")


if __name__ == "__main__":
    password = (
        sys.argv[1] if len(sys.argv) > 1 else config.administration.SUPER_ADMIN_PASSWORD
    )
    asyncio.run(reset_admin_password(password))
