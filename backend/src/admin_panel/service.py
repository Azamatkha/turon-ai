"""Admin foydalanuvchilarni boshqarish mantig'i."""
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
)
from src.core.utils.security import hash_password
from src.user.enums import UserRole
from src.user.models import User


class AdminUserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_users(
        self, search: str | None = None, department: str | None = None
    ) -> list[User]:
        stmt = select(User).where(User.is_deleted.is_(False))
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.username).like(like),
                    func.lower(User.first_name).like(like),
                    func.lower(User.last_name).like(like),
                )
            )
        if department:
            stmt = stmt.where(func.lower(User.department) == department.lower())
        stmt = stmt.order_by(User.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def create_user(
        self,
        username: str,
        full_name: str,
        password: str,
        role: UserRole,
        department: str | None,
    ) -> User:
        username = username.strip()
        exists = await self._session.execute(
            select(User).where(User.username == username, User.is_deleted.is_(False))
        )
        if exists.scalar_one_or_none():
            raise InstanceAlreadyExistsException("Bunday username allaqachon mavjud")

        parts = full_name.strip().split(maxsplit=1)
        first = parts[0][:50]
        last = (parts[1] if len(parts) > 1 else first)[:50]
        user = User(
            first_name=first,
            last_name=last,
            email=f"{username}@turon.local",
            username=username,
            phone_number="",
            department=(department or None),
            password_hash=hash_password(password),
            role=role,
            is_verified=True,
            is_active=True,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def _get(self, user_id: UUID) -> User:
        user = (
            await self._session.execute(
                select(User).where(User.id == user_id, User.is_deleted.is_(False))
            )
        ).scalar_one_or_none()
        if user is None:
            raise InstanceNotFoundException("Foydalanuvchi topilmadi")
        return user

    async def change_role(self, user_id: UUID, role: UserRole) -> User:
        user = await self._get(user_id)
        user.role = role
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def update_user(
        self,
        user_id: UUID,
        *,
        username: str | None = None,
        full_name: str | None = None,
        password: str | None = None,
        department: str | None = None,
    ) -> User:
        """Foydalanuvchining username/ism/parol/bo'limini tahrirlash (admin)."""
        user = await self._get(user_id)

        if username is not None and username.strip() and username.strip() != user.username:
            new_username = username.strip()
            exists = await self._session.execute(
                select(User).where(
                    User.username == new_username,
                    User.id != user_id,
                    User.is_deleted.is_(False),
                )
            )
            if exists.scalar_one_or_none():
                raise InstanceAlreadyExistsException("Bunday username allaqachon mavjud")
            user.username = new_username

        if full_name is not None and full_name.strip():
            parts = full_name.strip().split(maxsplit=1)
            user.first_name = parts[0][:50]
            user.last_name = (parts[1] if len(parts) > 1 else parts[0])[:50]

        if department is not None:
            user.department = department.strip() or None

        if password:
            user.password_hash = hash_password(password)

        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> None:
        user = await self._get(user_id)
        user.is_deleted = True
        user.is_active = False
        await self._session.commit()
