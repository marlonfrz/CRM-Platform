from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.db.dependencies import get_db_session
from app.models.activity import ActivityType
from app.policies.authorization import AuthorizationContext
from app.schemas.activities import ActivityCorrection, ActivityPage, ActivityRequest
from app.services.activities import correct_activity, create_activity, list_activities
from app.services.exceptions import DomainError

from .errors import domain_http_exception

router = APIRouter(prefix="/clients/{client_id}/activities", tags=["activities"])


@router.get("", response_model=ActivityPage)
async def get_activities(
    client_id: UUID,
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    activity_type: ActivityType | None = None,
    department_id: UUID | None = None,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ActivityPage:
    try:
        return await list_activities(
            session,
            authorization=authorization,
            client_id=client_id,
            activity_type=activity_type,
            department_id=department_id,
            offset=offset,
            limit=limit,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_activity(
    client_id: UUID,
    payload: ActivityRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, UUID]:
    try:
        activity = await create_activity(
            session,
            authorization=authorization,
            client_id=client_id,
            payload=payload,
        )
        return {"id": activity.id}
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.patch("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def patch_activity(
    client_id: UUID,
    activity_id: UUID,
    payload: ActivityCorrection,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        await correct_activity(
            session,
            authorization=authorization,
            client_id=client_id,
            activity_id=activity_id,
            payload=payload,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
