from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceNotFoundException,
    UnauthorizedException,
)
from src.core.storage.media import delete_media
from src.guides.storage import (
    append_chunk,
    cancel_upload,
    finalize_upload,
    start_upload,
)
from src.guides.models import EdoGuide
from src.guides.schemas import (
    CreateEdoGuideModel,
    EdoGuideView,
    GuideUploadChunkView,
    GuideUploadStartView,
    UpdateEdoGuideModel,
)
from src.guides.video_token import is_valid_video_token, make_video_token
from src.main.config import config

logger = get_logger(__name__)

GUIDE_NOT_FOUND = "Yo'riqnoma topilmadi"
BAD_VIDEO_TOKEN = "Video havolasi eskirgan yoki noto'g'ri"


def _to_view(guide: EdoGuide) -> EdoGuideView:
    return EdoGuideView(
        id=guide.id,
        title=guide.title,
        size_bytes=guide.size_bytes,
        video_url=f"/v1/guides/{guide.id}/video?token={make_video_token(guide.id)}",
        created_at=guide.created_at,
    )


class ListGuidesUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self) -> list[EdoGuideView]:
        async with self.uow as uow:
            guides = await uow.edo_guides.list_by_title(uow.session)
            return [_to_view(g) for g in guides]


class GetGuideVideoUseCase:
    """Imzoli token tekshirilgach videoning nisbiy yo'lini qaytaradi."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, guide_id: UUID, token: str) -> str:
        if not is_valid_video_token(guide_id, token):
            raise UnauthorizedException(BAD_VIDEO_TOKEN)
        async with self.uow as uow:
            guide = await uow.edo_guides.get_single(uow.session, id=guide_id)
        if guide is None:
            raise InstanceNotFoundException(GUIDE_NOT_FOUND)
        return guide.video_path


class StartGuideUploadUseCase:
    async def execute(self) -> GuideUploadStartView:
        upload_id = await start_upload()
        return GuideUploadStartView(
            upload_id=upload_id,
            chunk_size=8 * 1024 * 1024,
            max_bytes=config.app.GUIDE_VIDEO_MAX_BYTES,
        )


class AppendGuideChunkUseCase:
    async def execute(
        self, upload_id: UUID, offset: int, data: bytes
    ) -> GuideUploadChunkView:
        received = await append_chunk(
            upload_id, offset, data, max_total=config.app.GUIDE_VIDEO_MAX_BYTES
        )
        return GuideUploadChunkView(received=received)


class CancelGuideUploadUseCase:
    async def execute(self, upload_id: UUID) -> None:
        await cancel_upload(upload_id)


class CreateGuideUseCase:
    """Yig'ilgan videoni doimiy joyga ko'chiradi va bazaga yozadi.

    Baza yozuvi muvaffaqiyatsiz bo'lsa — ko'chirilgan fayl o'chiriladi (yetim
    fayl diskda qolib ketmasin).
    """

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, data: CreateEdoGuideModel, created_by: UUID
    ) -> EdoGuideView:
        video_path, size = await finalize_upload(data.upload_id)
        try:
            async with self.uow as uow:
                guide = await uow.edo_guides.create(
                    uow.session,
                    {
                        "title": data.title,
                        "video_path": video_path,
                        "size_bytes": size,
                        "created_by": created_by,
                    },
                )
                await uow.commit()
                return _to_view(guide)
        except Exception:
            await delete_media(video_path)
            raise


class UpdateGuideUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, guide_id: UUID, data: UpdateEdoGuideModel) -> EdoGuideView:
        async with self.uow as uow:
            guide = await uow.edo_guides.update(
                uow.session, {"title": data.title}, id=guide_id
            )
            if guide is None:
                raise InstanceNotFoundException(GUIDE_NOT_FOUND)
            await uow.commit()
            return _to_view(guide)


class DeleteGuideUseCase:
    """Yozuvni o'chiradi, commit'dan keyin faylni ham."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, guide_id: UUID) -> None:
        async with self.uow as uow:
            guide = await uow.edo_guides.delete(uow.session, id=guide_id)
            if guide is None:
                raise InstanceNotFoundException(GUIDE_NOT_FOUND)
            video_path = guide.video_path
            await uow.commit()
        await delete_media(video_path)
        logger.info("EDO yo'riqnomasi o'chirildi: %s", guide_id)


def get_list_guides_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListGuidesUseCase:
    return ListGuidesUseCase(uow=uow)


def get_guide_video_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> GetGuideVideoUseCase:
    return GetGuideVideoUseCase(uow=uow)


def get_start_guide_upload_use_case() -> StartGuideUploadUseCase:
    return StartGuideUploadUseCase()


def get_append_guide_chunk_use_case() -> AppendGuideChunkUseCase:
    return AppendGuideChunkUseCase()


def get_cancel_guide_upload_use_case() -> CancelGuideUploadUseCase:
    return CancelGuideUploadUseCase()


def get_create_guide_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CreateGuideUseCase:
    return CreateGuideUseCase(uow=uow)


def get_update_guide_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> UpdateGuideUseCase:
    return UpdateGuideUseCase(uow=uow)


def get_delete_guide_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> DeleteGuideUseCase:
    return DeleteGuideUseCase(uow=uow)
