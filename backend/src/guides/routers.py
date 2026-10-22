"""EDO yo'riqnomalari (video) endpointlari.

Ikkita router:
  • `router`       — /v1/guides       : kirgan har bir xodim ro'yxatni ko'radi,
                                        videoni imzoli havola orqali oladi
  • `admin_router` — /v1/admin/guides : admin video yuklaydi, nomini
                                        o'zgartiradi, o'chiradi

Yuklash BO'LAKLAB (nginx 10 MB limitiga tegmaslik uchun, batafsil —
`guides/storage.py`):
  POST   /admin/guides/uploads                     -> {upload_id, chunk_size}
  PUT    /admin/guides/uploads/{id}?offset=N       (tana — xom bayt, <= 9 MB)
  POST   /admin/guides  {upload_id, title}         -> tayyor yo'riqnoma
  DELETE /admin/guides/uploads/{id}                -> yuklashni bekor qilish

Video statik papkadan berilmaydi. `<video src>` Authorization header yubora
olmagani uchun ro'yxat har bir videoga qisqa muddatli imzoli `video_url`
beradi; `/video` endpointi shu tokenni tekshiradi. Video oldinga/orqaga
surilishi uchun javob HTTP Range'ni qo'llaydi (Starlette FileResponse).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from src.core.errors.exceptions import PayloadTooLargeException
from src.core.storage.media import resolve_media_path
from src.guides.schemas import (
    CreateEdoGuideModel,
    EdoGuideView,
    GuideUploadChunkView,
    GuideUploadStartView,
    UpdateEdoGuideModel,
)
from src.guides.usecases import (
    AppendGuideChunkUseCase,
    CancelGuideUploadUseCase,
    CreateGuideUseCase,
    StartGuideUploadUseCase,
    DeleteGuideUseCase,
    GetGuideVideoUseCase,
    ListGuidesUseCase,
    UpdateGuideUseCase,
    get_append_guide_chunk_use_case,
    get_cancel_guide_upload_use_case,
    get_create_guide_use_case,
    get_start_guide_upload_use_case,
    get_delete_guide_use_case,
    get_guide_video_use_case,
    get_list_guides_use_case,
    get_update_guide_use_case,
)
from src.user.auth.dependencies import get_current_user
from src.user.auth.permissions.checker import require_permission
from src.user.auth.permissions.enum import Permission
from src.main.config import config
from src.user.models import User

router = APIRouter()
admin_router = APIRouter()

CHUNK_TOO_LARGE = "Bo'lak juda katta"

EditSettingsUser = Annotated[
    User, Depends(require_permission(Permission.EDIT_SETTINGS))
]


async def _read_body_limited(request: Request, max_bytes: int) -> bytes:
    """So'rov tanasini o'qiydi; limitdan oshsa darhol to'xtatadi."""
    buffer = bytearray()
    async for part in request.stream():
        buffer.extend(part)
        if len(buffer) > max_bytes:
            raise PayloadTooLargeException(CHUNK_TOO_LARGE)
    return bytes(buffer)


@router.get("", response_model=list[EdoGuideView])
async def list_guides(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListGuidesUseCase, Depends(get_list_guides_use_case)],
) -> list[EdoGuideView]:
    """EDO yo'riqnomalari ro'yxati (sarlavha bo'yicha alifbo tartibida)."""
    return await use_case.execute()


@router.get("/{guide_id}/video")
async def get_guide_video(
    guide_id: UUID,
    token: Annotated[str, Query(min_length=1, max_length=200)],
    use_case: Annotated[GetGuideVideoUseCase, Depends(get_guide_video_use_case)],
) -> FileResponse:
    """Video fayl. Authorization header o'rniga ro'yxatdagi imzoli `token`."""
    relative_path = await use_case.execute(guide_id=guide_id, token=token)
    return FileResponse(
        resolve_media_path(relative_path),
        media_type="video/mp4",
        # Token muddati ichida brauzer qayta yuklamasin, lekin umumiy keshlarga tushmasin
        headers={"Cache-Control": "private, max-age=3600"},
    )


@admin_router.post(
    "/uploads", status_code=201, response_model=GuideUploadStartView
)
async def start_guide_upload(
    current_user: EditSettingsUser,
    use_case: Annotated[
        StartGuideUploadUseCase, Depends(get_start_guide_upload_use_case)
    ],
) -> GuideUploadStartView:
    """Admin: video yuklashni boshlaydi (bo'laklab yuklashning 1-qadami)."""
    return await use_case.execute()


@admin_router.put("/uploads/{upload_id}", response_model=GuideUploadChunkView)
async def append_guide_chunk(
    upload_id: UUID,
    request: Request,
    offset: Annotated[int, Query(ge=0)],
    current_user: EditSettingsUser,
    use_case: Annotated[
        AppendGuideChunkUseCase, Depends(get_append_guide_chunk_use_case)
    ],
) -> GuideUploadChunkView:
    """Admin: navbatdagi bo'lak (tana — xom bayt). `offset` — bo'lak fayl
    ichida qayerdan boshlanishi; u serverdagi hajmga teng bo'lishi shart."""
    data = await _read_body_limited(request, config.app.GUIDE_CHUNK_MAX_BYTES)
    return await use_case.execute(upload_id=upload_id, offset=offset, data=data)


@admin_router.delete("/uploads/{upload_id}", status_code=204)
async def cancel_guide_upload(
    upload_id: UUID,
    current_user: EditSettingsUser,
    use_case: Annotated[
        CancelGuideUploadUseCase, Depends(get_cancel_guide_upload_use_case)
    ],
) -> None:
    """Admin: tugallanmagan yuklashni bekor qiladi."""
    await use_case.execute(upload_id=upload_id)


@admin_router.post("", status_code=201, response_model=EdoGuideView)
async def create_guide(
    data: CreateEdoGuideModel,
    current_user: EditSettingsUser,
    use_case: Annotated[CreateGuideUseCase, Depends(get_create_guide_use_case)],
) -> EdoGuideView:
    """Admin: yuklangan videodan yo'riqnoma yaratadi (MP4, 200 MB gacha)."""
    return await use_case.execute(data=data, created_by=current_user.id)


@admin_router.patch("/{guide_id}", response_model=EdoGuideView)
async def update_guide(
    guide_id: UUID,
    data: UpdateEdoGuideModel,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    use_case: Annotated[UpdateGuideUseCase, Depends(get_update_guide_use_case)],
) -> EdoGuideView:
    """Admin: yo'riqnoma sarlavhasini o'zgartiradi."""
    return await use_case.execute(guide_id=guide_id, data=data)


@admin_router.delete("/{guide_id}", status_code=204)
async def delete_guide(
    guide_id: UUID,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    use_case: Annotated[DeleteGuideUseCase, Depends(get_delete_guide_use_case)],
) -> None:
    """Admin: yo'riqnomani va uning video faylini o'chiradi."""
    await use_case.execute(guide_id=guide_id)
