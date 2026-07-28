from datetime import timedelta

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.utils.datetime_utils import get_utc_now

from src.user.dependencies import get_user_repository
from src.user.repositories import UserRepository
from src.user.schemas import UserAdminListItem


class ListUsersUseCase:
    # Dashboard'dagi count_online bilan bir xil bo'lishi shart
    ONLINE_MINUTES = 5

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        session: AsyncSession,
        search: str | None,
        department: str | None,
    ) -> list[UserAdminListItem]:
        users = await self.repository.search_list(
            session, search=search, department=department
        )
        # Onlayn = oxirgi ONLINE_MINUTES daqiqada faollik ko'rsatgan
        cutoff = get_utc_now() - timedelta(minutes=self.ONLINE_MINUTES)
        items: list[UserAdminListItem] = []
        for u in users:
            item = UserAdminListItem.model_validate(u)
            seen = getattr(u, "last_seen_at", None)
            item.is_online = bool(seen and seen >= cutoff)
            items.append(item)
        return items


def get_list_users_use_case(
    repository: UserRepository = Depends(get_user_repository),
) -> ListUsersUseCase:
    return ListUsersUseCase(repository=repository)