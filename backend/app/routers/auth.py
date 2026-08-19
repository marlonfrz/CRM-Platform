from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.dependencies import Principal, get_current_principal, require_csrf
from app.config import Settings, get_settings
from app.db.dependencies import get_db_session
from app.schemas.auth import AuthenticatedUserResponse, ChangePasswordRequest, LoginRequest
from app.services.authentication import change_password, login, logout
from app.services.exceptions import InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthenticatedUserResponse)
async def login_route(
    payload: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUserResponse:
    try:
        _, user, session_token, csrf_token = await login(
            session, email=payload.email, password=payload.password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from exc

    set_auth_cookies(
        response,
        session_token=session_token,
        csrf_token=csrf_token,
        settings=settings,
    )
    return AuthenticatedUserResponse.model_validate(user)


@router.get("/me", response_model=AuthenticatedUserResponse)
async def current_user(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse.model_validate(principal.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_route(
    response: Response,
    principal: Annotated[Principal, Depends(require_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    await logout(session, user_session=principal.session, user=principal.user)
    clear_auth_cookies(response, settings)


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password_route(
    payload: ChangePasswordRequest,
    response: Response,
    principal: Annotated[Principal, Depends(require_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    try:
        await change_password(
            session,
            user=principal.user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is invalid"
        ) from exc
    clear_auth_cookies(response, settings)
