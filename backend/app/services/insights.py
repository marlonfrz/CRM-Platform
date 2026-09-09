from typing import Any, Literal
from uuid import UUID

from sqlalchemy import DateTime, Select, cast, func, literal, null, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Activity,
    Client,
    Department,
    DepartmentMember,
    OrganizationMode,
    Task,
    User,
    UserRole,
    UserStatus,
)
from app.policies.authorization import AuthorizationContext
from app.schemas.insights import (
    DashboardMetrics,
    DashboardResponse,
    DepartmentOverview,
    HistoryEntry,
    HistoryPage,
)
from app.services.clients import get_client
from app.services.scopes import visible_activities, visible_clients, visible_tasks


def _activity_rows(context: AuthorizationContext) -> Select[Any]:
    return (
        visible_activities(context)
        .with_only_columns(
            Activity.id.label("id"),
            literal("ACTIVITY").label("kind"),
            Activity.client_id.label("client_id"),
            Client.name.label("client_name"),
            Activity.department_id.label("department_id"),
            Department.name.label("department_name"),
            Activity.user_id.label("person_id"),
            User.full_name.label("person_name"),
            Activity.type.label("type"),
            Activity.type.label("title"),
            Activity.description.label("description"),
            Activity.next_action.label("next_action"),
            Activity.occurred_at.label("occurred_at"),
            cast(null(), DateTime(timezone=True)).label("due_at"),
        )
        .join(Client, Client.id == Activity.client_id)
        .join(User, User.id == Activity.user_id)
        .outerjoin(Department, Department.id == Activity.department_id)
    )


def _task_rows(context: AuthorizationContext) -> Select[Any]:
    return (
        visible_tasks(context)
        .with_only_columns(
            Task.id.label("id"),
            literal("TASK").label("kind"),
            Task.client_id.label("client_id"),
            Client.name.label("client_name"),
            Task.department_id.label("department_id"),
            Department.name.label("department_name"),
            Task.assigned_to_user_id.label("person_id"),
            User.full_name.label("person_name"),
            Task.status.label("type"),
            Task.title.label("title"),
            Task.description.label("description"),
            cast(null(), Activity.next_action.type).label("next_action"),
            func.coalesce(Task.completed_at, Task.created_at).label("occurred_at"),
            Task.due_at.label("due_at"),
        )
        .join(Client, Client.id == Task.client_id)
        .join(User, User.id == Task.assigned_to_user_id)
        .outerjoin(Department, Department.id == Task.department_id)
    )


async def _entries(session: AsyncSession, statement: Select[Any]) -> list[HistoryEntry]:
    return [
        HistoryEntry.model_validate(row) for row in (await session.execute(statement)).mappings()
    ]


async def client_history(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    kind: Literal["ACTIVITY", "TASK"] | None = None,
    offset: int = 0,
    limit: int = 20,
) -> HistoryPage:
    await get_client(session, authorization=authorization, client_id=client_id)
    activities = _activity_rows(authorization).where(Activity.client_id == client_id)
    tasks = _task_rows(authorization).where(Task.client_id == client_id)
    combined = (
        activities
        if kind == "ACTIVITY"
        else tasks
        if kind == "TASK"
        else union_all(activities, tasks)
    ).subquery()
    entries = await _entries(
        session,
        select(combined)
        .order_by(
            combined.c.occurred_at.desc(),
            combined.c.kind.asc(),
            combined.c.id.desc(),
        )
        .offset(offset)
        .limit(limit + 1),
    )
    return HistoryPage(items=entries[:limit], has_more=len(entries) > limit)


def _count(statement: Select[Any]) -> Any:
    return select(func.count()).select_from(statement.subquery()).scalar_subquery()


async def dashboard(
    session: AsyncSession, *, authorization: AuthorizationContext
) -> DashboardResponse:
    activity_scope = visible_activities(authorization)
    task_scope = visible_tasks(authorization)
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
                    _count(task_scope.where(Task.status == "PENDING")).label("pending_tasks"),
                    _count(task_scope.where(Task.status == "COMPLETED")).label("completed_tasks"),
                    _count(activity_scope).label("activities"),
                    (_count(user_scope) if management else null()).label("active_users"),
                    (_count(department_scope) if management else null()).label("departments"),
                )
            )
        )
        .mappings()
        .one()
    )
    departments = []
    if management:
        act = activity_scope.subquery()
        work = task_scope.where(Task.status == "PENDING").subquery()
        act_counts = (
            select(act.c.department_id, func.count().label("count"))
            .group_by(act.c.department_id)
            .subquery()
        )
        work_counts = (
            select(work.c.department_id, func.count().label("count"))
            .group_by(work.c.department_id)
            .subquery()
        )
        employee_counts = (
            select(
                DepartmentMember.department_id, func.count(func.distinct(User.id)).label("count")
            )
            .join(
                User,
                User.id == DepartmentMember.user_id,
            )
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
                    func.coalesce(act_counts.c.count, 0).label("activities"),
                    func.coalesce(work_counts.c.count, 0).label("pending_tasks"),
                )
                .outerjoin(employee_counts, employee_counts.c.department_id == Department.id)
                .outerjoin(act_counts, act_counts.c.department_id == Department.id)
                .outerjoin(work_counts, work_counts.c.department_id == Department.id)
                .order_by(Department.name, Department.id)
            )
        ).mappings()
        departments = [DepartmentOverview.model_validate(row) for row in rows]
    recent = await _entries(
        session,
        _activity_rows(authorization)
        .order_by(Activity.occurred_at.desc(), Activity.id.desc())
        .limit(5),
    )
    pending = await _entries(
        session,
        _task_rows(authorization)
        .where(Task.status == "PENDING")
        .order_by(
            Task.due_at.asc().nulls_last(),
            Task.created_at.desc(),
            Task.id.desc(),
        )
        .limit(5),
    )
    return DashboardResponse(
        metrics=DashboardMetrics.model_validate(counters),
        departments=departments,
        recent_activities=recent,
        pending_tasks=pending,
    )
