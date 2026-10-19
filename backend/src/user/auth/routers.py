from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.core.limiter.depends import RateLimiter
from src.core.schemas import SuccessResponse, TokenModel
from src.user.auth.dependencies import (
    AuthenticatedUser,
    get_access_by_refresh_token,
    get_current_user_with_session,
    get_user_id_from_token,
)
from src.user.auth.jwt_payload_schema import JWTPayload
from src.user.auth.schemas import (
    CheckFaceTokenModel,
    LoginTokenModel,
    LoginUserModel,
    LogoutRequestModel,
    TuronIdSignInModel,
    RegisterTokenModel,
    RegisterUserModel,
    SaveSignatureModel,
)
from src.user.auth.usecases.check_face_token import (
    CheckFaceTokenUseCase,
    get_check_face_token_use_case,
)
from src.user.auth.usecases.get_access_by_refresh import (
    GetTokensByRefreshUserUseCase,
    get_tokens_by_refresh_user_use_case,
)
from src.user.auth.usecases.login import LoginUserUseCase, get_login_user_use_case
from src.user.auth.usecases.logout import LogoutUseCase, get_logout_use_case
from src.user.auth.usecases.register import RegisterUseCase, get_register_use_case
from src.user.auth.usecases.save import (
    SaveSignatureUseCase,
    get_save_signature_use_case,
)
from src.user.auth.turon_id.usecase import (
    TuronIdSignInUseCase,
    get_turon_id_sign_in_use_case,
)
from src.user.models import User

router = APIRouter()


@router.post(
    "/register",
    status_code=201,
    response_model=RegisterTokenModel,
    dependencies=[Depends(RateLimiter(times=10, minutes=10))],
)
async def signup_user(
    user_form_data: RegisterUserModel,
    use_case: Annotated[RegisterUseCase, Depends(get_register_use_case)],
) -> RegisterTokenModel:
    """
    Mobil ilova: login + parol bilan ro'yxatdan o'tish.

    User tasdiqlanmagan (`is_verified=false`) holda yaratiladi va darhol
    faqat access token qaytadi — keyingi qadam Face-ID verifikatsiyasi.
    """
    return await use_case.execute(data=user_form_data)


@router.post(
    "/save",
    response_model=SuccessResponse,
    dependencies=[Depends(RateLimiter(times=10, minutes=10))],
)
async def save_face_id_result(
    form_data: SaveSignatureModel,
    use_case: Annotated[SaveSignatureUseCase, Depends(get_save_signature_use_case)],
) -> SuccessResponse:
    """
    Mobil: Face-ID natijasini (GSI imzosi) saqlab, ro'yxatdan o'tishni yakunlash.

    Authorization header kerak emas — user imzo ichidagi accessToken'dan olinadi.
    `{"success": true}` — akkaunt tasdiqlandi; `{"success": false}` — xodim emas.
    """
    return await use_case.execute(data=form_data)


@router.post(
    "/check-face-token",
    response_model=SuccessResponse,
)
async def check_face_token(
    form_data: CheckFaceTokenModel,
    use_case: Annotated[
        CheckFaceTokenUseCase, Depends(get_check_face_token_use_case)
    ],
) -> SuccessResponse:
    """
    mTLS proxy: SDK so'rovini GSI'ga uzatishdan OLDIN accessToken'ni tekshiradi.

    `200 {"success": true}` — token yaroqli, proxy so'rovni GSI'ga yuboradi.
    `401` — token yo'q / imzo noto'g'ri / muddati o'tgan / verificationId
    topilmadi: proxy SDK'ga 401 qaytaradi, GSI'ga va webhook'ga bormaydi.
    """
    return await use_case.execute(token=form_data.token)


@router.post(
    "/login",
    response_model=LoginTokenModel,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login_user(
    login_form_data: LoginUserModel,
    use_case: Annotated[LoginUserUseCase, Depends(get_login_user_use_case)],
) -> LoginTokenModel:
    """
    Authenticate user and return tokens.

    Javobda `is_verified` ham bor — mobil ilova login'dan keyin darhol
    chatga yoki Face-ID verifikatsiyasiga yo'naltirishi uchun.
    """
    return await use_case.execute(data=login_form_data)


@router.post(
    "/login/refresh",
    response_model=TokenModel,
    dependencies=[
        Depends(  # IP-based rate limiting
            RateLimiter(
                times=20,
                minutes=15,
            )
        ),
        Depends(  # User-based rate limiting
            RateLimiter(
                times=5,
                minutes=15,
                identifier=get_user_id_from_token,
            )
        ),
    ],
)
async def get_access_by_refresh(
    user_and_payload: Annotated[
        tuple[User, JWTPayload], Depends(get_access_by_refresh_token)
    ],
    use_case: Annotated[
        GetTokensByRefreshUserUseCase, Depends(get_tokens_by_refresh_user_use_case)
    ],
) -> TokenModel:
    """
    Refresh the access token using a valid refresh token.
    """
    current_user, old_payload = user_and_payload

    return await use_case.execute(user=current_user, old_token_payload=old_payload)


@router.post(
    "/logout",
    response_model=SuccessResponse,
)
async def logout_user(
    authenticated: Annotated[AuthenticatedUser, Depends(get_current_user_with_session)],
    use_case: Annotated[LogoutUseCase, Depends(get_logout_use_case)],
    data: Annotated[LogoutRequestModel | None, Body()] = None,
) -> SuccessResponse:
    """
    Invalidate the current session or all user sessions.
    """
    return await use_case.execute(
        user_id=str(authenticated.user.id),
        session_id=authenticated.session_id,
        terminate_all_sessions=(
            data.terminate_all_sessions if data is not None else False
        ),
    )


@router.post(
    "/turon-id",
    response_model=LoginTokenModel,
    summary="Sign in through Turon ID (web).",
    description=(
        "The Turon ID portal opens the chat with a one-time code in the URL "
        "fragment; the web app posts it here. The backend exchanges it with "
        "Turon ID and returns a normal chat session. The user is linked by "
        "Turon ID account, then by phone, or created; always verified."
    ),
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def turon_id_sign_in(
    payload: TuronIdSignInModel,
    use_case: Annotated[TuronIdSignInUseCase, Depends(get_turon_id_sign_in_use_case)],
) -> LoginTokenModel:
    return await use_case.execute(payload.code)
