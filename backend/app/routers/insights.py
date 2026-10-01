from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_authorization_context
from app.db.dependencies import get_db_session
from app.models.activity import ActivityStatus
from app.policies.authorization import AuthorizationContext
from app.schemas.insights import DashboardResponse, HistoryPage
from app.services.exceptions import DomainError
from app.services.insights import client_history, dashboard

from .errors import domain_http_exception

router = APIRouter(tags=["insights"])
Authorization = Annotated[AuthorizationContext, Depends(get_authorization_context)]
Database = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(authorization: Authorization, session: Database) -> DashboardResponse:
    return await dashboard(session, authorization=authorization)


@router.get("/clients/{client_id}/history", response_model=HistoryPage)
async def get_history(
    client_id: UUID,
    authorization: Authorization,
    session: Database,
    activity_status: ActivityStatus | None = None,
    activity_type_id: UUID | None = None,
    scheduled: bool | None = None,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> HistoryPage:
    try:
        return await client_history(
            session,
            authorization=authorization,
            client_id=client_id,
            activity_status=activity_status,
            activity_type_id=activity_type_id,
            scheduled=scheduled,
            offset=offset,
            limit=limit,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
