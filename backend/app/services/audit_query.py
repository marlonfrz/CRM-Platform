from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.policies.authorization import AuthorizationContext, can_view_audit
from app.schemas.audit import AuditEntry, AuditPage, readable_metadata
from app.services.exceptions import AuthorizationDeniedError


async def list_audit_events(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    action: str | None = None,
    actor_user_id: UUID | None = None,
    entity_id: UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> AuditPage:
    if not can_view_audit(authorization, authorization.organization_id):
        raise AuthorizationDeniedError("Audit access is restricted to the owner")
    statement = (
        select(AuditLog, User.full_name)
        .outerjoin(
            User,
            and_(
                User.id == AuditLog.actor_user_id, User.organization_id == AuditLog.organization_id
            ),
        )
        .where(AuditLog.organization_id == authorization.organization_id)
    )
    if action:
        statement = statement.where(AuditLog.action == action)
    if actor_user_id:
        statement = statement.where(AuditLog.actor_user_id == actor_user_id)
    if entity_id:
        statement = statement.where(AuditLog.entity_id == entity_id)
    if since:
        statement = statement.where(AuditLog.created_at >= since)
    if until:
        statement = statement.where(AuditLog.created_at <= until)
    rows = list(
        await session.execute(
            statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    )
    return AuditPage(
        items=[
            AuditEntry(
                id=event.id,
                actor_user_id=event.actor_user_id,
                actor_name=actor_name,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                created_at=event.created_at,
                metadata=readable_metadata(event.action, event.entity_type, event.event_data),
            )
            for event, actor_name in rows[:limit]
        ],
        has_more=len(rows) > limit,
    )
