from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import (
    Activity,
    ActivityType,
    Client,
    Department,
    DepartmentMember,
    OrganizationMode,
    User,
    UserRole,
    UserStatus,
)
from app.models.activity import ActivityStatus
from app.policies.activities import can_correct_activity
from app.policies.authorization import AuthorizationContext, can_manage_task
from app.schemas.insights import (
    DashboardMetrics,
    DashboardResponse,
    DepartmentOverview,
    HistoryEntry,
    HistoryPage,
)
from app.services.clients import get_client
from app.services.recurrence import materialize_schedules
from app.services.scopes import visible_activities, visible_clients


def _activity_rows(context: AuthorizationContext) -> Select[Any]:
    assignee = aliased(User)
    return (
        visible_activities(context)
        .add_columns(
            Client.name.label("client_name"),
            Department.name.label("department_name"),
            assignee.full_name.label("person_name"),
            ActivityType.name.label("activity_type_name"),
        )
        .join(Client, Client.id == Activity.client_id)
        .join(assignee, assignee.id == Activity.assigned_to_user_id)
        .outerjoin(Department, Department.id == Activity.department_id)
        .join(ActivityType, ActivityType.id == Activity.activity_type_id)
    )


def _entry(
    authorization: AuthorizationContext,
    row: Any,
) -> HistoryEntry:
    activity: Activity = row[0]
    pending = activity.status == ActivityStatus.PENDING.value
    can_edit = (
        can_manage_task(
            authorization,
            organization_id=activity.organization_id,
            department_id=activity.department_id,
            is_assigned_to_actor=activity.assigned_to_user_id == authorization.user_id,
            is_client_assigned=True,
        )
        if pending
        else can_correct_activity(
            authorization,
            organization_id=activity.organization_id,
            department_id=activity.department_id,
            author_id=activity.user_id,
            created_at=activity.created_at,
            now=datetime.now(UTC),
            is_client_assigned=True,
        )
    )
    return HistoryEntry(
        id=activity.id,
        client_id=activity.client_id,
        client_name=row.client_name,
        department_id=activity.department_id,
        department_name=row.department_name,
        person_id=activity.assigned_to_user_id,
        person_name=row.person_name,
        activity_type_id=activity.activity_type_id,
        activity_type_name=row.activity_type_name,
        title=activity.title,
        description=activity.description,
        next_action=activity.next_action,
        scheduled_for=activity.scheduled_for,
        status=ActivityStatus(activity.status),
        occurred_at=activity.occurred_at,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
        completed_at=activity.completed_at,
        schedule_id=activity.schedule_id,
        can_edit=can_edit,
        can_delete=pending and can_edit,
    )


async def _entries(
    session: AsyncSession,
    statement: Select[Any],
    authorization: AuthorizationContext,
) -> list[HistoryEntry]:
    return [_entry(authorization, row) for row in (await session.execute(statement)).all()]


async def client_history(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    activity_status: ActivityStatus | None = None,
    activity_type_id: UUID | None = None,
    scheduled: bool | None = None,
    offset: int = 0,
    limit: int = 20,
) -> HistoryPage:
    await get_client(session, authorization=authorization, client_id=client_id)
    await materialize_schedules(
        session, organization_id=authorization.organization_id, client_id=client_id
    )
    statement = _activity_rows(authorization).where(Activity.client_id == client_id)
    if activity_status is not None:
        statement = statement.where(Activity.status == activity_status.value)
    if activity_type_id is not None:
        statement = statement.where(Activity.activity_type_id == activity_type_id)
    if scheduled is True:
        statement = statement.where(Activity.scheduled_for > date.today())
    elif scheduled is False:
        statement = statement.where(Activity.scheduled_for <= date.today())
    rows = await _entries(
        session,
        statement.order_by(
            Activity.scheduled_for.desc(), Activity.created_at.desc(), Activity.id.desc()
        )
        .offset(offset)
        .limit(limit + 1),
        authorization,
    )
    return HistoryPage(items=rows[:limit], has_more=len(rows) > limit)


def _count(statement: Select[Any]) -> Any:
    return select(func.count()).select_from(statement.subquery()).scalar_subquery()


async def dashboard(
    session: AsyncSession, *, authorization: AuthorizationContext
) -> DashboardResponse:
    await materialize_schedules(session, organization_id=authorization.organization_id)
    activity_scope = visible_activities(authorization)
    department_scope = select(Department).where(
        Department.organization_id == authorization.organization_id
    )
    user_scope = select(User).where(
        User.organization_id == authorization.organization_id, User.status == UserStatus.ACTIVE
    )
    management = (
        authorization.organization_mode is OrganizationMode.BUSINESS
        and authorization.role != UserRole.EMPLOYEE
    )
    today_start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
    tomorrow_start = today_start + timedelta(days=1)
    today_condition = or_(
        Activity.scheduled_for == date.today(),
        (
            (Activity.completed_at >= today_start)
            & (Activity.completed_at < tomorrow_start)
        ),
    )
    today_scope = activity_scope.where(today_condition)
    today_rows = today_scope.subquery()
    if not authorization.is_owner:
        department_scope = department_scope.where(Department.id.in_(authorization.department_ids))
        user_scope = user_scope.where(
            User.role == UserRole.EMPLOYEE,
            select(DepartmentMember.id)
            .where(
                DepartmentMember.user_id == User.id,
                DepartmentMember.organization_id == authorization.organization_id,
                DepartmentMember.department_id.in_(authorization.department_ids),
            )
            .exists(),
        )
    counters = (
        (
            await session.execute(
                select(
                    _count(visible_clients(authorization)).label("clients"),
                    _count(activity_scope.where(Activity.status == "PENDING")).label(
                        "pending_tasks"
                    ),
                    _count(
                        activity_scope.where(
                            Activity.status == ActivityStatus.COMPLETED.value,
                            Activity.completed_at >= today_start,
                            Activity.completed_at < tomorrow_start,
                        )
                    ).label("completed_tasks"),
                    _count(activity_scope).label("activities"),
                    select(func.count(func.distinct(today_rows.c.client_id)))
                    .scalar_subquery()
                    .label("today_clients"),
                    _count(today_scope).label("today_activities"),
                    _count(
                        activity_scope.where(
                            Activity.status == ActivityStatus.PENDING.value,
                            Activity.scheduled_for == date.today(),
                        )
                    ).label("today_pending_tasks"),
                    (_count(user_scope) if management else null()).label("active_users"),
                    (_count(department_scope) if management else null()).label("departments"),
                )
            )
        )
        .mappings()
        .one()
    )
    departments: list[DepartmentOverview] = []
    if management:
        all_work = today_scope.subquery()
        pending_scope = activity_scope.where(
            Activity.status == ActivityStatus.PENDING.value,
            Activity.scheduled_for == date.today(),
        ).subquery()
        activity_counts = (
            select(all_work.c.department_id, func.count().label("count"))
            .group_by(all_work.c.department_id)
            .subquery()
        )
        pending_counts = (
            select(pending_scope.c.department_id, func.count().label("count"))
            .group_by(pending_scope.c.department_id)
            .subquery()
        )
        employee_counts = (
            select(
                DepartmentMember.department_id, func.count(func.distinct(User.id)).label("count")
            )
            .join(User, User.id == DepartmentMember.user_id)
            .where(
                User.organization_id == authorization.organization_id,
                DepartmentMember.organization_id == authorization.organization_id,
                User.role == UserRole.EMPLOYEE,
                User.status == UserStatus.ACTIVE,
            )
            .group_by(DepartmentMember.department_id)
            .subquery()
        )
        rows = (
            await session.execute(
                department_scope.with_only_columns(
                    Department.id,
                    Department.name,
                    func.coalesce(employee_counts.c.count, 0).label("active_employees"),
                    func.coalesce(activity_counts.c.count, 0).label("activities"),
                    func.coalesce(pending_counts.c.count, 0).label("pending_tasks"),
                )
                .outerjoin(employee_counts, employee_counts.c.department_id == Department.id)
                .outerjoin(activity_counts, activity_counts.c.department_id == Department.id)
                .outerjoin(pending_counts, pending_counts.c.department_id == Department.id)
                .order_by(Department.name, Department.id)
            )
        ).mappings()
        departments = [DepartmentOverview.model_validate(row) for row in rows]
    recent = await _entries(
        session,
        _activity_rows(authorization)
        .where(Activity.status == ActivityStatus.COMPLETED.value)
        .order_by(Activity.completed_at.desc(), Activity.id.desc())
        .limit(5),
        authorization,
    )
    pending_entries = await _entries(
        session,
        _activity_rows(authorization)
        .where(Activity.status == ActivityStatus.PENDING.value)
        .order_by(Activity.scheduled_for.asc(), Activity.created_at.desc(), Activity.id.desc())
        .limit(5),
        authorization,
    )
    today_entries = await _entries(
        session,
        _activity_rows(authorization)
        .where(today_condition)
        .order_by(Activity.scheduled_for.asc(), Activity.created_at.desc(), Activity.id.desc())
        .limit(8),
        authorization,
    )
    return DashboardResponse(
        metrics=DashboardMetrics.model_validate(counters),
        departments=departments,
        today_activities=today_entries,
        recent_activities=recent,
        pending_tasks=pending_entries,
    )
