from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.db.dependencies import get_db_session
from app.policies import AuthorizationContext
from app.schemas.assignments import (
    AssignmentRequest,
    AssignmentTeamResponse,
    AssignmentUserResponse,
)
from app.services.assignments import assign_client, list_team, unassign_client
from app.services.exceptions import DomainError

from .errors import domain_http_exception

router = APIRouter(prefix="/clients/{client_id}/assignments", tags=["assignments"])


@router.get("", response_model=AssignmentTeamResponse)
async def get_team(
    client_id: UUID,
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AssignmentTeamResponse:
    try:
        assigned, available = await list_team(
            session, authorization=authorization, client_id=client_id
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return AssignmentTeamResponse(
        assigned=[
            AssignmentUserResponse(user_id=u.id, full_name=u.full_name, status=u.status)
            for u in assigned
        ],
        available=[
            AssignmentUserResponse(user_id=u.id, full_name=u.full_name, status=u.status)
            for u in available
        ],
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_assignment(
    client_id: UUID,
    payload: AssignmentRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        await assign_client(
            session, authorization=authorization, client_id=client_id, user_id=payload.user_id
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    client_id: UUID,
    user_id: UUID,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        await unassign_client(
            session, authorization=authorization, client_id=client_id, user_id=user_id
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
