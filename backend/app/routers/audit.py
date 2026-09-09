from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_authorization_context
from app.db.dependencies import get_db_session
from app.policies.authorization import AuthorizationContext
from app.schemas.audit import AuditPage
from app.services.audit_query import list_audit_events
from app.services.exceptions import DomainError

from .errors import domain_http_exception

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=AuditPage)
async def get_audit(
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    action: Annotated[str | None, Query(pattern=r"^[A-Z_]+$", max_length=80)] = None,
    actor_user_id: UUID | None = None,
    entity_id: UUID | None = None,
    since: AwareDatetime | None = None,
    until: AwareDatetime | None = None,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AuditPage:
    if since is not None and until is not None and since > until:
        raise HTTPException(status_code=422, detail="since must not be after until")
    try:
        return await list_audit_events(
            session,
            authorization=authorization,
            action=action,
            actor_user_id=actor_user_id,
            entity_id=entity_id,
            since=since,
            until=until,
            offset=offset,
            limit=limit,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
