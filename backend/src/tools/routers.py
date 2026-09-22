"""
Yordamchi dasturlar (mini-ilovalar) endpointlari — hozircha PDF konvertor.

Web va mobil ilova bir xil endpointdan foydalanadi.

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) /v1/users/auth/login orqali access_token oling va "Authorize" ga kiriting.
2) POST /v1/tools/convert/to-pdf — `files` maydoniga bitta .docx/.xlsx/.pptx
   yoki bir nechta rasm (jpg/png) tanlang -> javobda PDF fayl.
─────────────────────────────────────────────────────────────────────────────
"""

import re
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile

from src.core.limiter.depends import RateLimiter
from src.tools.usecases import ConvertToPdfUseCase, get_convert_to_pdf_use_case
from src.user.auth.dependencies import get_current_user, get_user_id_from_token
from src.user.models import User

router = APIRouter()


@router.post(
    "/convert/to-pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
    dependencies=[
        Depends(RateLimiter(times=30, minutes=60, identifier=get_user_id_from_token))
    ],
)
async def convert_to_pdf(
    files: Annotated[list[UploadFile], File(description="Bitta hujjat yoki 1-20 ta rasm")],
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ConvertToPdfUseCase, Depends(get_convert_to_pdf_use_case)],
) -> Response:
    """
    Word (.doc/.docx/.odt/.rtf), Excel (.xls/.xlsx/.ods), PowerPoint
    (.ppt/.pptx/.odp) hujjatini yoki rasmlarni (jpg/png/webp/bmp/tiff) PDF'ga
    o'giradi. Rasmlar yuborilgan tartibda bitta PDF'ga yig'iladi. Fayllar
    serverda saqlanmaydi.
    """
    result = await use_case.execute(files)
    # Kirill/lotin nomlar ham buzilmasin — RFC 5987 (filename*), eski
    # mijozlar uchun esa ASCII zaxira nom
    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", result.filename[:-4]).strip("._")
    ascii_name = f"{ascii_stem if re.search(r'[A-Za-z0-9]', ascii_stem) else 'document'}.pdf"
    disposition = (
        f'attachment; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(result.filename)}"
    )
    return Response(
        content=result.content,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition},
    )
