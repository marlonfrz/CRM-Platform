from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Activity, ActivitySchedule, ActivityType, Department, OrganizationMode, User
from app.models.activity import ActivityStatus
from app.models.enums import UserRole
from app.policies.activities import can_correct_activity
from app.policies.authorization import AuthorizationContext, can_create_activity, can_manage_task
from app.schemas.activities import (
    ActivityCandidate,
    ActivityDepartment,
    ActivityPage,
    ActivityPeriod,
    ActivityRequest,
    ActivityResponse,
    ActivityTypeOption,
    ActivityUpdate,
    DeleteScope,
    LegacyActivityType,
)
from app.services.activity_options import activity_options
from app.services.activity_types import list_activity_types, require_activity_type
from app.services.audit import add_audit_event
from app.services.client_access import lock_accessible_client
from app.services.clients import get_client
from app.services.departments import list_departments
from app.services.exceptions import (
    AuthorizationDeniedError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.services.recurrence import (
    materialize_next,
    materialize_schedules,
    occurrence_from_schedule,
    schedule_from_rule,
)
from app.services.scopes import visible_activities


def _visible(authorization: AuthorizationContext, client_id: UUID) -> Select[tuple[Activity]]:
    return visible_activities(authorization).where(Activity.client_id == client_id)


def _can_edit(authorization: AuthorizationContext, activity: Activity) -> bool:
    if activity.status == ActivityStatus.PENDING.value:
        return can_manage_task(
            authorization,
            organization_id=activity.organization_id,
            department_id=activity.department_id,
            is_assigned_to_actor=activity.assigned_to_user_id == authorization.user_id,
            is_client_assigned=True,
        )
    return can_correct_activity(
        authorization,
        organization_id=activity.organization_id,
        department_id=activity.department_id,
        author_id=activity.user_id,
        created_at=activity.created_at,
        now=datetime.now(UTC),
        is_client_assigned=True,
    )


def _can_delete(authorization: AuthorizationContext, activity: Activity) -> bool:
    return activity.status == ActivityStatus.PENDING.value and can_manage_task(
        authorization,
        organization_id=activity.organization_id,
        department_id=activity.department_id,
        is_assigned_to_actor=activity.assigned_to_user_id == authorization.user_id,
        is_client_assigned=True,
    )


LEGACY_TYPE_NAMES = {
    LegacyActivityType.CALL: "llamada",
    LegacyActivityType.EMAIL: "email",
    LegacyActivityType.MEETING: "reunión",
    LegacyActivityType.NOTE: "nota",
    LegacyActivityType.INCIDENT: "incidencia",
    LegacyActivityType.OTHER: "otro",
}
LEGACY_NAMES_TO_CODES = {value: key.value for key, value in LEGACY_TYPE_NAMES.items()}


async def _resolve_activity_type(
    session: AsyncSession,
    authorization: AuthorizationContext,
    activity_type_id: UUID | None,
    legacy_type: LegacyActivityType | None,
    department_id: UUID | None,
) -> ActivityType:
    if activity_type_id is not None:
        return await require_activity_type(
            session, authorization, activity_type_id, department_id
        )
    activity_type = await session.scalar(
        select(ActivityType).where(
            ActivityType.organization_id == authorization.organization_id,
            ActivityType.department_id.is_(None),
            ActivityType.normalized_name
            == LEGACY_TYPE_NAMES[legacy_type or LegacyActivityType.OTHER],
            ActivityType.is_active.is_(True),
        )
    )
    if activity_type is None:
        raise ResourceNotFoundError("Activity type not found")
    return activity_type


async def _department(
    session: AsyncSession,
    authorization: AuthorizationContext,
    requested: UUID | None,
) -> tuple[UUID | None, list[Department]]:
    departments = await list_departments(session, authorization=authorization)
    if authorization.organization_mode is OrganizationMode.INDIVIDUAL:
        if requested is not None:
            raise AuthorizationDeniedError("Individual activities have no department")
        return None, departments
    allowed_ids = {item.id for item in departments}
    department_id = requested
    if department_id is None and len(allowed_ids) == 1:
        department_id = next(iter(allowed_ids))
    if department_id is None:
        raise ResourceConflictError("Choose an available department")
    if department_id not in allowed_ids:
        raise AuthorizationDeniedError("Department outside your scope")
    return department_id, departments


async def _assignee(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
    department_id: UUID | None,
    requested: UUID | None,
) -> tuple[UUID, list[ActivityCandidate]]:
    options = await activity_options(session, authorization, client_id)
    candidates = [
        ActivityCandidate(id=item.id, name=item.name, department_ids=item.department_ids)
        for item in options.candidates
    ]
    target_id = requested or authorization.user_id
    candidate = next((item for item in candidates if item.id == target_id), None)
    if candidate is None or (
        not options.individual and department_id not in candidate.department_ids
    ):
        raise AuthorizationDeniedError(
            "Assignee is inactive, outside scope or has no client access"
        )
    return target_id, candidates


def _response(
    authorization: AuthorizationContext,
    activity: Activity,
    creator_name: str,
    assignee_name: str,
    department_name: str | None,
    activity_type_name: str,
) -> ActivityResponse:
    return ActivityResponse(
        id=activity.id,
        client_id=activity.client_id,
        user_id=activity.user_id,
        user_name=creator_name,
        assigned_to_user_id=activity.assigned_to_user_id,
        assigned_to_name=assignee_name,
        department_id=activity.department_id,
        department_name=department_name,
        activity_type_id=activity.activity_type_id,
        activity_type_name=activity_type_name,
        type=LEGACY_NAMES_TO_CODES.get(activity_type_name.casefold(), "OTHER"),
        title=activity.title,
        description=activity.description,
        next_action=activity.next_action,
        scheduled_for=activity.scheduled_for,
        status=ActivityStatus(activity.status),
        occurred_at=activity.occurred_at,
        completed_at=activity.completed_at,
        schedule_id=activity.schedule_id,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
        can_edit=_can_edit(authorization, activity),
        can_delete=_can_delete(authorization, activity),
    )


async def list_activities(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_type_id: UUID | None = None,
    legacy_type: LegacyActivityType | None = None,
    department_id: UUID | None = None,
    status: ActivityStatus | None = None,
    period: ActivityPeriod | None = None,
    scheduled: bool | None = None,
    offset: int = 0,
    limit: int = 20,
) -> ActivityPage:
    await get_client(session, authorization=authorization, client_id=client_id)
    await materialize_schedules(
        session, organization_id=authorization.organization_id, client_id=client_id
    )
    departments = await list_departments(session, authorization=authorization)
    options = await activity_options(session, authorization, client_id)
    activity_types = await list_activity_types(session, authorization)
    statement = _visible(authorization, client_id)
    if activity_type_id is not None:
        statement = statement.where(Activity.activity_type_id == activity_type_id)
    if legacy_type is not None:
        statement = statement.where(
            ActivityType.normalized_name == LEGACY_TYPE_NAMES[legacy_type]
        )
    if department_id is not None:
        statement = statement.where(Activity.department_id == department_id)
    if status is not None:
        statement = statement.where(Activity.status == status.value)
    if period is ActivityPeriod.TODAY:
        statement = statement.where(Activity.scheduled_for == date.today())
    elif period is ActivityPeriod.SCHEDULED:
        statement = statement.where(
            Activity.scheduled_for > date.today(),
            Activity.status == ActivityStatus.PENDING.value,
        )
    elif period is ActivityPeriod.HISTORY:
        statement = statement.where(Activity.scheduled_for < date.today())
    elif scheduled is True:
        statement = statement.where(Activity.scheduled_for > date.today())
    elif scheduled is False:
        statement = statement.where(Activity.scheduled_for <= date.today())
    creator = aliased(User)
    assignee = aliased(User)
    ordering = (
        (Activity.scheduled_for.asc(), Activity.created_at.asc(), Activity.id.asc())
        if period is ActivityPeriod.SCHEDULED or (period is None and scheduled is True)
        else (Activity.scheduled_for.desc(), Activity.created_at.desc(), Activity.id.desc())
    )
    rows = (
        await session.execute(
            statement.add_columns(
                creator.full_name,
                assignee.full_name,
                Department.name,
                ActivityType.name,
            )
            .join(creator, creator.id == Activity.user_id)
            .join(assignee, assignee.id == Activity.assigned_to_user_id)
            .outerjoin(Department, Department.id == Activity.department_id)
            .join(ActivityType, ActivityType.id == Activity.activity_type_id)
            .order_by(*ordering)
            .offset(offset)
            .limit(limit + 1)
        )
    ).all()
    can_create = bool(options.candidates) and (
        authorization.organization_mode is OrganizationMode.INDIVIDUAL or bool(departments)
    )
    return ActivityPage(
        items=[_response(authorization, *row) for row in rows[:limit]],
        departments=[ActivityDepartment(id=item.id, name=item.name) for item in departments],
        candidates=[
            ActivityCandidate(id=item.id, name=item.name, department_ids=item.department_ids)
            for item in options.candidates
        ],
        activity_types=[
            ActivityTypeOption(id=item.id, name=item.name, department_id=item.department_id)
            for item in activity_types
        ],
        can_create=can_create,
        can_manage_types=authorization.role is not UserRole.EMPLOYEE,
        has_more=len(rows) > limit,
    )


async def create_activity(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    payload: ActivityRequest,
) -> list[Activity]:
    await lock_accessible_client(session, authorization, client_id)
    department_id, _ = await _department(
        session, authorization, payload.department_id
    )
    target_id, _ = await _assignee(
        session,
        authorization,
        client_id,
        department_id,
        payload.assigned_to_user_id,
    )
    activity_type = await _resolve_activity_type(
        session,
        authorization,
        payload.activity_type_id,
        payload.type,
        department_id,
    )
    manager = can_manage_task(
        authorization,
        organization_id=authorization.organization_id,
        department_id=department_id,
        is_assigned_to_actor=target_id == authorization.user_id,
        is_client_assigned=True,
    )
    creator = can_create_activity(
        authorization,
        organization_id=authorization.organization_id,
        department_id=department_id,
        is_client_assigned=True,
    )
    if (payload.status is ActivityStatus.PENDING and not manager) or (
        payload.status is ActivityStatus.COMPLETED and not creator
    ):
        raise AuthorizationDeniedError("Activity creation is not allowed")

    common = dict(
        organization_id=authorization.organization_id,
        client_id=client_id,
        user_id=authorization.user_id,
        assigned_to_user_id=target_id,
        department_id=department_id,
        activity_type_id=activity_type.id,
        title=payload.title
        or (payload.description[:200] if payload.status is ActivityStatus.PENDING else None),
        description=payload.description,
        next_action=payload.next_action or None,
    )
    activities: list[Activity]
    if payload.recurrence is not None:
        schedule = schedule_from_rule(
            rule=payload.recurrence,
            starts_on=payload.scheduled_for,
            organization_id=authorization.organization_id,
            client_id=client_id,
            created_by_user_id=authorization.user_id,
            assigned_to_user_id=target_id,
            department_id=department_id,
            activity_type_id=activity_type.id,
            title=common["title"],
            description=payload.description,
            next_action=payload.next_action or None,
        )
        session.add(schedule)
        await session.flush()
        first = occurrence_from_schedule(schedule, payload.scheduled_for)
        session.add(first)
        activities = [first]
        following = materialize_next(session, schedule)
        if following is not None:
            activities.append(following)
    else:
        completed_at = datetime.now(UTC) if payload.status is ActivityStatus.COMPLETED else None
        activity = Activity(
            **common,
            schedule_id=None,
            scheduled_for=payload.scheduled_for,
            status=payload.status.value,
            occurred_at=(payload.occurred_at or completed_at)
            if payload.status is ActivityStatus.COMPLETED
            else None,
            completed_at=completed_at,
        )
        session.add(activity)
        activities = [activity]
    await session.flush()
    for activity in activities:
        _audit(session, authorization, activity, "CREATED_ACTIVITY", [])
    return activities


async def _managed_activity(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_id: UUID,
) -> Activity:
    await lock_accessible_client(session, authorization, client_id)
    activity = await session.scalar(
        _visible(authorization, client_id).where(Activity.id == activity_id).with_for_update()
    )
    if activity is None:
        raise ResourceNotFoundError("Activity not found")
    if not _can_edit(authorization, activity):
        raise AuthorizationDeniedError("Activity management is not allowed")
    return activity


async def update_activity(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_id: UUID,
    payload: ActivityUpdate,
) -> None:
    activity = await _managed_activity(session, authorization, client_id, activity_id)
    target_id, _ = await _assignee(
        session,
        authorization,
        client_id,
        activity.department_id,
        payload.assigned_to_user_id or activity.assigned_to_user_id,
    )
    activity_type = await _resolve_activity_type(
        session,
        authorization,
        payload.activity_type_id,
        payload.type,
        activity.department_id,
    )
    values = {
        "activity_type_id": activity_type.id,
        "title": payload.title,
        "description": payload.description,
        "next_action": payload.next_action or None,
        "scheduled_for": payload.scheduled_for or activity.scheduled_for,
        "assigned_to_user_id": target_id,
    }
    if activity.status == ActivityStatus.COMPLETED.value and payload.occurred_at is not None:
        values["occurred_at"] = payload.occurred_at
    changed = [key for key, value in values.items() if getattr(activity, key) != value]
    for key, value in values.items():
        setattr(activity, key, value)
    if changed:
        await session.flush()
        _audit(session, authorization, activity, "UPDATED_ACTIVITY", changed)


async def complete_activity(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_id: UUID,
) -> None:
    await lock_accessible_client(session, authorization, client_id)
    activity = await session.scalar(
        _visible(authorization, client_id).where(Activity.id == activity_id).with_for_update()
    )
    if activity is None:
        raise ResourceNotFoundError("Activity not found")
    if activity.status == ActivityStatus.COMPLETED.value:
        if not can_manage_task(
            authorization,
            organization_id=activity.organization_id,
            department_id=activity.department_id,
            is_assigned_to_actor=activity.assigned_to_user_id == authorization.user_id,
            is_client_assigned=True,
        ):
            raise AuthorizationDeniedError("Activity management is not allowed")
        return
    if not _can_edit(authorization, activity):
        raise AuthorizationDeniedError("Activity management is not allowed")
    completed_at = datetime.now(UTC)
    activity.status = ActivityStatus.COMPLETED.value
    activity.occurred_at = completed_at
    activity.completed_at = completed_at
    await session.flush()
    _audit(
        session,
        authorization,
        activity,
        "COMPLETED_ACTIVITY",
        ["status", "occurred_at", "completed_at"],
    )


async def delete_activity(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_id: UUID,
    scope: DeleteScope,
) -> None:
    await lock_accessible_client(session, authorization, client_id)
    activity = await session.scalar(
        _visible(authorization, client_id).where(Activity.id == activity_id).with_for_update()
    )
    if activity is None:
        raise ResourceNotFoundError("Activity not found")
    if not _can_delete(authorization, activity):
        raise AuthorizationDeniedError("Only manageable pending activities can be deleted")
    if scope == "THIS_AND_FOLLOWING" and activity.schedule_id is not None:
        schedule = await session.scalar(
            select(ActivitySchedule)
            .where(
                ActivitySchedule.id == activity.schedule_id,
                ActivitySchedule.organization_id == authorization.organization_id,
            )
            .with_for_update()
        )
        if schedule is not None:
            schedule.active = False
        await session.execute(
            delete(Activity).where(
                Activity.schedule_id == activity.schedule_id,
                Activity.scheduled_for >= activity.scheduled_for,
                Activity.status == ActivityStatus.PENDING.value,
            )
        )
    else:
        await session.delete(activity)
    add_audit_event(
        session,
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        action="DELETED_ACTIVITY",
        entity_type="ACTIVITY",
        entity_id=activity_id,
        event_data={"client_id": str(client_id), "scope": scope},
    )


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
            "assigned_to_user_id": str(activity.assigned_to_user_id),
            "department_id": str(activity.department_id) if activity.department_id else None,
            "schedule_id": str(activity.schedule_id) if activity.schedule_id else None,
            "changed_fields": changed,
        },
    )
