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
    CreateUserModel,
    LoginUserModel,
    LogoutRequestModel,
)
from src.user.auth.usecases.get_access_by_refresh import (
    GetTokensByRefreshUserUseCase,
    get_tokens_by_refresh_user_use_case,
)
from src.user.auth.usecases.login import LoginUserUseCase, get_login_user_use_case
from src.user.auth.usecases.logout import LogoutUseCase, get_logout_use_case
from src.user.auth.usecases.register import RegisterUseCase, get_register_use_case
from src.user.models import User
from src.user.schemas import (
    UserProfileViewModel,
)

router = APIRouter()


@router.post(
    "/register",
    status_code=201,
    response_model=UserProfileViewModel,
    dependencies=[Depends(RateLimiter(times=10, minutes=10))],
)
async def signup_user(
    user_form_data: CreateUserModel,
    use_case: Annotated[RegisterUseCase, Depends(get_register_use_case)],
) -> UserProfileViewModel:
    """
    Create a new user account.
    """
    return await use_case.execute(data=user_form_data)


@router.post(
    "/login",
    response_model=TokenModel,
    dependencies=[Depends(RateLimiter(times=2, seconds=60))],
)
async def login_user(
    login_form_data: LoginUserModel,
    use_case: Annotated[LoginUserUseCase, Depends(get_login_user_use_case)],
) -> TokenModel:
    """
    Authenticate user and return tokens.
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
