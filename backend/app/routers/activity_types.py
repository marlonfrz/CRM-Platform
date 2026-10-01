from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.db.dependencies import get_db_session
from app.policies.authorization import AuthorizationContext
from app.schemas.activities import ActivityTypeOption, ActivityTypeRequest
from app.services.activity_types import create_activity_type, list_activity_types
from app.services.exceptions import DomainError

from .errors import domain_http_exception

router = APIRouter(prefix="/activity-types", tags=["activity-types"])


@router.get("", response_model=list[ActivityTypeOption])
async def get_activity_types(
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ActivityTypeOption]:
    return [
        ActivityTypeOption(id=item.id, name=item.name, department_id=item.department_id)
        for item in await list_activity_types(session, authorization)
    ]


@router.post("", response_model=ActivityTypeOption, status_code=status.HTTP_201_CREATED)
async def post_activity_type(
    payload: ActivityTypeRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ActivityTypeOption:
    try:
        return await create_activity_type(
            session,
            authorization=authorization,
            name=payload.name,
            department_id=payload.department_id,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
