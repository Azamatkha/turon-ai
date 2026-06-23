"""Oddiy auth biznes mantig'i: ro'yxatdan o'tish, login, foydalanuvchini topish."""
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors.exceptions import InstanceAlreadyExistsException
from src.core.utils.security import hash_password, normalize_email, verify_password
from src.user.enums import UserRole
from src.user.models import User


def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(maxsplit=1)
    first = parts[0][:50]
    last = (parts[1] if len(parts) > 1 else "")[:50]
    return first, last


class SimpleAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def authenticate(self, login: str, password: str) -> User | None:
        """login = username yoki email. To'g'ri bo'lsa User, aks holda None."""
        stmt = select(User).where(
            or_(User.username == login, User.email == normalize_email(login)),
            User.is_deleted.is_(False),
            User.is_active.is_(True),
        )
        user = (await self._session.execute(stmt)).scalar_one_or_none()
        if user and await verify_password(password, user.password_hash):
            return user
        return None

    async def register(
        self, username: str, full_name: str, password: str, department: str | None
    ) -> User:
        """Yangi foydalanuvchi (default role=USER). username band bo'lsa 409."""
        username = username.strip()
        exists = await self._session.execute(
            select(User).where(User.username == username, User.is_deleted.is_(False))
        )
        if exists.scalar_one_or_none():
            raise InstanceAlreadyExistsException("Bunday username allaqachon mavjud")

        first, last = _split_full_name(full_name)
        user = User(
            first_name=first,
            last_name=last or first,
            email=f"{username}@turon.local",  # oddiy auth uchun email shart emas
            username=username,
            phone_number="",
            department=(department or None),
            password_hash=hash_password(password),
            role=UserRole.USER,
            is_verified=True,
            is_active=True,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        try:
            uid = UUID(user_id)
        except ValueError:
            return None
        stmt = select(User).where(User.id == uid, User.is_deleted.is_(False))
        return (await self._session.execute(stmt)).scalar_one_or_none()
