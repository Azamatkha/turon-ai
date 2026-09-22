from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors.exceptions import InstanceProcessingException
from src.user.dependencies import get_user_repository
from src.user.repositories import UserRepository
from src.user.schemas import DirectoryEntryModel

# Bir so'rovda qaytadigan eng ko'p qator — bitta bo'limdagi xodimlar bundan kam
DIRECTORY_LIMIT = 200
# Ism bo'yicha qidiruvning eng qisqa uzunligi ("a" bilan butun bankni qaytarmasin)
MIN_SEARCH_LEN = 2


class DirectoryUseCase:
    """Xodimlar ma'lumotnomasi: bo'lim tanlanadi -> xodimlar ro'yxati chiqadi ->
    har birida ism, lavozim, bo'lim va ichki IP raqam.

    Web va mobil ilova bir xil endpointlardan foydalanadi.
    """

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def departments(self, session: AsyncSession) -> list[str]:
        return await self.repository.directory_departments(session)

    async def search(
        self,
        session: AsyncSession,
        department: str | None,
        q: str | None,
    ) -> list[DirectoryEntryModel]:
        department = (department or "").strip() or None
        q = (q or "").strip() or None
        # Butun ro'yxatni bir yo'la tortib olishning oldini olamiz: yoki bo'lim,
        # yoki kamida 2 belgili qidiruv bo'lishi shart.
        if not department and (not q or len(q) < MIN_SEARCH_LEN):
            raise InstanceProcessingException(
                "Bo'limni tanlang yoki kamida 2 ta belgi kiriting"
            )
        users = await self.repository.directory_search(
            session, department=department, search=q, limit=DIRECTORY_LIMIT
        )
        return [DirectoryEntryModel.model_validate(u) for u in users]


def get_directory_use_case(
    repository: UserRepository = Depends(get_user_repository),
) -> DirectoryUseCase:
    return DirectoryUseCase(repository=repository)
