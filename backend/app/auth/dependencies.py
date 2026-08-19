from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import set_auth_cookies
from app.config import Settings, get_settings
from app.db.dependencies import get_db_session
from app.models import DepartmentMember, Organization, User, UserSession
from app.policies import AuthorizationContext
from app.services.authentication import authenticate_session
from app.services.exceptions import InvalidSessionError


@dataclass(frozen=True)
class Principal:
    user: User
    session: UserSession
    session_token: str
    csrf_token: str


async def get_current_principal(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    session_token = request.cookies.get(settings.session_cookie_name)
    csrf_token = request.cookies.get(settings.csrf_cookie_name)
    if not session_token or not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    try:
        user_session, user = await authenticate_session(session, session_token=session_token)
    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session"
        ) from exc

    set_auth_cookies(
        response,
        session_token=session_token,
        csrf_token=csrf_token,
        settings=settings,
    )
    return Principal(
        user=user,
        session=user_session,
        session_token=session_token,
        csrf_token=csrf_token,
    )


async def require_csrf(
    principal: Annotated[Principal, Depends(get_current_principal)],
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> Principal:
    if not csrf_header or not compare_digest(csrf_header, principal.csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    if not compare_digest(
        sha256(csrf_header.encode()).hexdigest(), principal.session.csrf_token_hash
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    return principal


async def get_authorization_context(
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthorizationContext:
    organization_mode = await session.scalar(
        select(Organization.mode).where(Organization.id == principal.user.organization_id)
    )
    if organization_mode is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    department_ids = frozenset(
        await session.scalars(
            select(DepartmentMember.department_id).where(
                DepartmentMember.organization_id == principal.user.organization_id,
                DepartmentMember.user_id == principal.user.id,
            )
        )
    )
    return AuthorizationContext(
        user_id=principal.user.id,
        organization_id=principal.user.organization_id,
        organization_mode=organization_mode,
        role=principal.user.role,
        department_ids=department_ids,
    )
