from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


def add_audit_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID,
    event_data: dict[str, Any] | None = None,
) -> AuditLog:
    event = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        event_data=event_data or {},
    )
    session.add(event)
    return event
