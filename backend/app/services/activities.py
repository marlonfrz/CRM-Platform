from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, Department, OrganizationMode, User
from app.models.activity import ActivityType
from app.policies.activities import can_correct_activity
from app.policies.authorization import AuthorizationContext, can_create_activity
from app.schemas.activities import (
    ActivityCorrection,
    ActivityDepartment,
    ActivityPage,
    ActivityRequest,
    ActivityResponse,
)
from app.services.audit import add_audit_event
from app.services.client_access import lock_accessible_client
from app.services.clients import get_client
from app.services.departments import list_departments
from app.services.exceptions import (
    AuthorizationDeniedError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def _visible(authorization: AuthorizationContext, client_id: UUID) -> Select[tuple[Activity]]:
    statement = select(Activity).where(
        Activity.organization_id == authorization.organization_id,
        Activity.client_id == client_id,
    )
    if authorization.organization_mode is OrganizationMode.INDIVIDUAL:
        statement = statement.where(Activity.department_id.is_(None))
    elif not authorization.is_owner:
        statement = statement.where(Activity.department_id.in_(authorization.department_ids))
    else:
        statement = statement.where(Activity.department_id.is_not(None))
    return statement


def _can_edit(authorization: AuthorizationContext, activity: Activity) -> bool:
    return can_correct_activity(
        authorization,
        organization_id=activity.organization_id,
        department_id=activity.department_id,
        author_id=activity.user_id,
        created_at=activity.created_at,
        now=datetime.now(UTC),
        is_client_assigned=True,
    )


async def list_activities(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_type: ActivityType | None = None,
    department_id: UUID | None = None,
    offset: int = 0,
    limit: int = 20,
) -> ActivityPage:
    await get_client(session, authorization=authorization, client_id=client_id)
    departments = await list_departments(session, authorization=authorization)
    statement = _visible(authorization, client_id)
    if activity_type is not None:
        statement = statement.where(Activity.type == activity_type.value)
    if department_id is not None:
        statement = statement.where(Activity.department_id == department_id)
    rows = (
        await session.execute(
            statement.add_columns(User.full_name, Department.name)
            .join(User, User.id == Activity.user_id)
            .outerjoin(Department, Department.id == Activity.department_id)
            .order_by(Activity.occurred_at.desc(), Activity.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    ).all()
    return ActivityPage(
        items=[
            ActivityResponse(
                id=activity.id,
                user_id=activity.user_id,
                user_name=user_name,
                department_id=activity.department_id,
                department_name=department_name,
                type=ActivityType(activity.type),
                description=activity.description,
                next_action=activity.next_action,
                occurred_at=activity.occurred_at,
                created_at=activity.created_at,
                updated_at=activity.updated_at,
                can_edit=_can_edit(authorization, activity),
            )
            for activity, user_name, department_name in rows[:limit]
        ],
        departments=[ActivityDepartment(id=d.id, name=d.name) for d in departments],
        can_create=bool(departments)
        or (
            authorization.organization_mode is OrganizationMode.INDIVIDUAL
            and authorization.is_owner
        ),
        has_more=len(rows) > limit,
    )


async def create_activity(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    payload: ActivityRequest,
) -> Activity:
    await lock_accessible_client(session, authorization, client_id)
    department_id = payload.department_id
    if authorization.organization_mode is OrganizationMode.INDIVIDUAL:
        if department_id is not None:
            raise AuthorizationDeniedError("Individual activities have no department")
    else:
        departments = await list_departments(session, authorization=authorization)
        allowed_ids = {d.id for d in departments}
        if department_id is None and len(allowed_ids) == 1:
            department_id = next(iter(allowed_ids))
        if department_id is None:
            raise ResourceConflictError("Choose an available department")
        if department_id not in allowed_ids:
            raise AuthorizationDeniedError("Department outside your scope")
        department = await session.scalar(
            select(Department)
            .where(
                Department.id == department_id,
                Department.organization_id == authorization.organization_id,
            )
            .with_for_update(read=True)
        )
        if department is None:
            raise ResourceNotFoundError("Department no longer exists")
    if not can_create_activity(
        authorization,
        organization_id=authorization.organization_id,
        department_id=department_id,
        is_client_assigned=True,
    ):
        raise AuthorizationDeniedError("Activity creation is not allowed")
    activity = Activity(
        organization_id=authorization.organization_id,
        client_id=client_id,
        user_id=authorization.user_id,
        department_id=department_id,
        type=payload.type.value,
        description=payload.description,
        next_action=payload.next_action or None,
        occurred_at=payload.occurred_at,
    )
    session.add(activity)
    await session.flush()
    _audit(session, authorization, activity, "CREATED_ACTIVITY", [])
    return activity


async def correct_activity(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_id: UUID,
    payload: ActivityCorrection,
) -> None:
    await lock_accessible_client(session, authorization, client_id)
    activity = await session.scalar(
        _visible(authorization, client_id)
        .where(
            Activity.id == activity_id,
        )
        .with_for_update()
    )
    if activity is None:
        raise ResourceNotFoundError("Activity not found")
    if not _can_edit(authorization, activity):
        raise AuthorizationDeniedError("Correction is not allowed or the 24 hour window expired")
    values = payload.model_dump()
    values["type"] = payload.type.value
    values["next_action"] = payload.next_action or None
    changed = [key for key, value in values.items() if getattr(activity, key) != value]
    for key, value in values.items():
        setattr(activity, key, value)
    if changed:
        await session.flush()
        _audit(session, authorization, activity, "UPDATED_ACTIVITY", changed)


def _audit(
    session: AsyncSession,
    authorization: AuthorizationContext,
    activity: Activity,
    action: str,
    changed: list[str],
) -> None:
    add_audit_event(
        session,
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        action=action,
        entity_type="ACTIVITY",
        entity_id=activity.id,
        event_data={
            "client_id": str(activity.client_id),
            "user_id": str(activity.user_id),
            "department_id": str(activity.department_id) if activity.department_id else None,
            "changed_fields": changed,
        },
    )
