from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, get_current_principal
from app.db.dependencies import get_db_session
from app.models import Department, Organization
from app.policies import AuthorizationContext
from app.schemas.workspace import DepartmentSummary, WorkspaceResponse

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("", response_model=WorkspaceResponse)
async def get_workspace(
    principal: Annotated[Principal, Depends(get_current_principal)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceResponse:
    departments = list(
        await session.scalars(
            select(Department)
            .where(
                Department.organization_id == authorization.organization_id,
                Department.id.in_(authorization.department_ids),
            )
            .order_by(Department.name)
        )
    )
    organization = await session.get(Organization, authorization.organization_id)
    if organization is None:
        raise RuntimeError("Authenticated organization no longer exists")
    return WorkspaceResponse(
        organization_id=organization.id,
        organization_name=organization.name,
        organization_mode=organization.mode,
        user_id=principal.user.id,
        user_name=principal.user.full_name,
        user_email=principal.user.email,
        user_role=principal.user.role,
        departments=[DepartmentSummary.model_validate(item) for item in departments],
    )
