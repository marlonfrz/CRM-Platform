from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.db.dependencies import get_db_session
from app.models import Organization
from app.policies import AuthorizationContext
from app.schemas.administration import (
    DepartmentRequest,
    DepartmentResponse,
    OrganizationResponse,
    UpdateOrganizationRequest,
)
from app.services.departments import (
    create_authorized_department,
    delete_department,
    list_departments,
    update_department,
)
from app.services.exceptions import DomainError
from app.services.organization import update_organization

from .errors import domain_http_exception

router = APIRouter(prefix="/admin", tags=["administration"])


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
