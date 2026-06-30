from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.dependencies import get_user_repository
from src.user.repositories import UserRepository
from src.user.schemas import UserAdminListItem


class ListUsersUseCase:
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
        return [UserAdminListItem.model_validate(u) for u in users]


def get_list_users_use_case(
    repository: UserRepository = Depends(get_user_repository),
) -> ListUsersUseCase:
    return ListUsersUseCase(repository=repository)