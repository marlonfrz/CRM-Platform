from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.config import Settings, get_settings
from app.db.dependencies import get_db_session
from app.models import Organization, User
from app.policies import AuthorizationContext
from app.schemas.administration import (
    CreateUserRequest,
    DepartmentRequest,
    DepartmentResponse,
    OrganizationResponse,
    UpdateOrganizationRequest,
    UpdateUserRequest,
    UserResponse,
)
from app.services.departments import (
    create_authorized_department,
    delete_department,
    list_departments,
    update_department,
)
from app.services.exceptions import DomainError
from app.services.organization import update_organization
from app.services.users import (
    activate_user,
    create_user,
    disable_authorized_user,
    list_authorized_users,
    resend_invitation,
    update_user,
)

from .errors import domain_http_exception

router = APIRouter(prefix="/admin", tags=["administration"])


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        department_ids=[item.department_id for item in user.department_memberships],
    )


@router.get("/organization", response_model=OrganizationResponse)
async def get_organization(
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrganizationResponse:
    organization = await session.get(Organization, authorization.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return OrganizationResponse.model_validate(organization)


@router.patch("/organization", response_model=OrganizationResponse)
async def patch_organization(
    payload: UpdateOrganizationRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrganizationResponse:
    try:
        organization = await update_organization(
            session, authorization=authorization, name=payload.name
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return OrganizationResponse.model_validate(organization)


@router.get("/departments", response_model=list[DepartmentResponse])
async def get_departments(
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DepartmentResponse]:
    departments = await list_departments(session, authorization=authorization)
    return [DepartmentResponse.model_validate(department) for department in departments]


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def post_department(
    payload: DepartmentRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DepartmentResponse:
    try:
        department = await create_authorized_department(
            session, authorization=authorization, name=payload.name
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return DepartmentResponse.model_validate(department)


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
async def patch_department(
    department_id: UUID,
    payload: DepartmentRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DepartmentResponse:
    try:
        department = await update_department(
            session,
            authorization=authorization,
            department_id=department_id,
            name=payload.name,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return DepartmentResponse.model_validate(department)


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_department(
    department_id: UUID,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        await delete_department(session, authorization=authorization, department_id=department_id)
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[UserResponse]:
    users = await list_authorized_users(session, authorization=authorization)
    return [user_response(user) for user in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def post_user(
    payload: CreateUserRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    try:
        user = await create_user(
            session,
            authorization=authorization,
            settings=settings,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            department_ids=frozenset(payload.department_ids),
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return user_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def patch_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    try:
        user = await update_user(
            session,
            authorization=authorization,
            user_id=user_id,
            full_name=payload.full_name,
            role=payload.role,
            department_ids=frozenset(payload.department_ids),
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return user_response(user)


@router.post("/users/{user_id}/disable", response_model=UserResponse)
async def post_disable_user(
    user_id: UUID,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    try:
        user = await disable_authorized_user(session, authorization=authorization, user_id=user_id)
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return user_response(user)


@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def post_activate_user(
    user_id: UUID,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    try:
        user = await activate_user(session, authorization=authorization, user_id=user_id)
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return user_response(user)


@router.post("/users/{user_id}/invitation", response_model=UserResponse)
async def post_resend_invitation(
    user_id: UUID,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    try:
        user = await resend_invitation(
            session,
            authorization=authorization,
            settings=settings,
            user_id=user_id,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return user_response(user)
