from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Activity,
    ActivityType,
    AuditLog,
    Client,
    ClientContact,
    Department,
    Organization,
    User,
)
from app.policies.authorization import AuthorizationContext, can_view_audit
from app.schemas.audit import (
    AUDIT_CATEGORY_ACTIONS,
    AuditActorOption,
    AuditCategory,
    AuditEntry,
    AuditPage,
    readable_metadata,
)
from app.services.exceptions import AuthorizationDeniedError


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


async def list_audit_events(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    action: str | None = None,
    category: AuditCategory | None = None,
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
                User.id == AuditLog.actor_user_id,
                User.organization_id == AuditLog.organization_id,
            ),
        )
        .where(AuditLog.organization_id == authorization.organization_id)
    )
    if action:
        statement = statement.where(AuditLog.action == action)
    if category:
        statement = statement.where(AuditLog.action.in_(AUDIT_CATEGORY_ACTIONS[category]))
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
    visible_rows = rows[:limit]
    metadata_by_id = {
        event.id: readable_metadata(event.action, event.entity_type, event.event_data)
        for event, _ in visible_rows
    }

    user_rows = (
        (
            await session.execute(
                select(User.id, User.full_name)
                .where(User.organization_id == authorization.organization_id)
                .order_by(User.full_name, User.id)
            )
        )
        .tuples()
        .all()
    )
    user_names: dict[UUID, str] = dict(user_rows)
    department_ids: set[UUID] = set()
    client_ids: set[UUID] = set()
    contact_ids: set[UUID] = set()
    activity_ids: set[UUID] = set()
    for event, _ in visible_rows:
        metadata = metadata_by_id[event.id]
        for key in ("department_id",):
            if identifier := _uuid(metadata.get(key)):
                department_ids.add(identifier)
        for key in ("department_ids", "previous_department_ids"):
            department_ids.update(
                identifier
                for value in metadata.get(key, [])
                if (identifier := _uuid(value)) is not None
            )
        if identifier := _uuid(metadata.get("client_id")):
            client_ids.add(identifier)
        if event.entity_type == "DEPARTMENT":
            department_ids.add(event.entity_id)
        elif event.entity_type == "CLIENT":
            client_ids.add(event.entity_id)
        elif event.entity_type == "CLIENT_CONTACT":
            contact_ids.add(event.entity_id)
        elif event.entity_type in {"ACTIVITY", "TASK"}:
            activity_ids.add(event.entity_id)

    department_names: dict[UUID, str] = (
        dict(
            (
                await session.execute(
                    select(Department.id, Department.name).where(
                        Department.organization_id == authorization.organization_id,
                        Department.id.in_(department_ids),
                    )
                )
            ).tuples().all()
        )
        if department_ids
        else {}
    )
    client_names: dict[UUID, str] = (
        dict(
            (
                await session.execute(
                    select(Client.id, Client.name).where(
                        Client.organization_id == authorization.organization_id,
                        Client.id.in_(client_ids),
                    )
                )
            ).tuples().all()
        )
        if client_ids
        else {}
    )
    contact_names: dict[UUID, str] = (
        dict(
            (
                await session.execute(
                    select(ClientContact.id, ClientContact.full_name).where(
                        ClientContact.organization_id == authorization.organization_id,
                        ClientContact.id.in_(contact_ids),
                    )
                )
            ).tuples().all()
        )
        if contact_ids
        else {}
    )
    activity_names = (
        {
            identifier: f"{type_name} · {client_name}"
            for identifier, type_name, client_name in (
                await session.execute(
                    select(Activity.id, ActivityType.name, Client.name)
                    .join(ActivityType, ActivityType.id == Activity.activity_type_id)
                    .join(Client, Client.id == Activity.client_id)
                    .where(
                        Activity.organization_id == authorization.organization_id,
                        Activity.id.in_(activity_ids),
                    )
                )
            ).tuples().all()
        }
        if activity_ids
        else {}
    )
    organization_name = await session.scalar(
        select(Organization.name).where(Organization.id == authorization.organization_id)
    )

    def metadata_names(metadata: dict[str, Any]) -> dict[str, str | list[str]]:
        names: dict[str, str | list[str]] = {}
        single_maps = {
            "client_id": client_names,
            "user_id": user_names,
            "assigned_to_user_id": user_names,
            "previous_assigned_to_user_id": user_names,
            "department_id": department_names,
        }
        for key, values in single_maps.items():
            identifier = _uuid(metadata.get(key))
            if identifier is not None and identifier in values:
                names[key] = values[identifier]
        for key in ("department_ids", "previous_department_ids"):
            resolved = [
                department_names[identifier]
                for value in metadata.get(key, [])
                if (identifier := _uuid(value)) in department_names
            ]
            if resolved:
                names[key] = resolved
        return names

    def entity_name(event: AuditLog, metadata: dict[str, Any]) -> str | None:
        if event.entity_type in {"ORGANIZATION", "AI_CONFIGURATION"}:
            return organization_name
        if event.entity_type == "USER":
            return user_names.get(event.entity_id) or metadata.get("full_name")
        if event.entity_type == "DEPARTMENT":
            return department_names.get(event.entity_id) or metadata.get("name")
        if event.entity_type == "CLIENT":
            return client_names.get(event.entity_id) or metadata.get("name")
        if event.entity_type == "CLIENT_CONTACT":
            return contact_names.get(event.entity_id) or metadata.get("full_name")
        if event.entity_type in {"ACTIVITY", "TASK"}:
            client_id = _uuid(metadata.get("client_id"))
            client_name = client_names.get(client_id) if client_id is not None else None
            return activity_names.get(event.entity_id) or (
                f"Actividad · {client_name}" if client_name else "Actividad"
            )
        if event.entity_type == "CLIENT_ASSIGNMENT":
            client_id = _uuid(metadata.get("client_id"))
            user_id = _uuid(metadata.get("user_id"))
            parts = [
                user_names.get(user_id) if user_id is not None else None,
                client_names.get(client_id) if client_id is not None else None,
            ]
            return " · ".join(part for part in parts if part) or "Asignación de cliente"
        if event.entity_type == "AI_SUMMARY":
            client_id = _uuid(metadata.get("client_id"))
            department_id = _uuid(metadata.get("department_id"))
            return (
                (client_names.get(client_id) if client_id is not None else None)
                or (
                    department_names.get(department_id)
                    if department_id is not None
                    else None
                )
                or organization_name
            )
        return None

    return AuditPage(
        items=[
            AuditEntry(
                id=event.id,
                actor_user_id=event.actor_user_id,
                actor_name=actor_name,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                entity_name=entity_name(event, metadata_by_id[event.id]),
                created_at=event.created_at,
                metadata=metadata_by_id[event.id],
                metadata_names=metadata_names(metadata_by_id[event.id]),
            )
            for event, actor_name in visible_rows
        ],
        actors=[AuditActorOption(id=identifier, name=name) for identifier, name in user_rows],
        has_more=len(rows) > limit,
    )
