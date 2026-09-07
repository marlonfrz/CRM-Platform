from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Client,
    ClientAssignment,
    Department,
    OrganizationMode,
    Task,
    User,
    UserRole,
    UserStatus,
)
from app.models.task import TaskStatus
from app.policies.authorization import AuthorizationContext, can_manage_task
from app.schemas.tasks import (
    TaskCandidate,
    TaskDepartment,
    TaskOptions,
    TaskPage,
    TaskRequest,
    TaskResponse,
    TaskUpdate,
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


def _visible(authorization: AuthorizationContext) -> Select[tuple[Task]]:
    statement = select(Task).where(Task.organization_id == authorization.organization_id)
    if authorization.organization_mode is OrganizationMode.INDIVIDUAL:
        statement = statement.where(Task.department_id.is_(None))
    elif not authorization.is_owner:
        statement = statement.where(Task.department_id.in_(authorization.department_ids))
    if authorization.role is UserRole.ADMIN:
        statement = statement.where(
            or_(
                Task.assigned_to_user_id == authorization.user_id,
                select(User.id)
                .where(
                    User.id == Task.assigned_to_user_id,
                    User.organization_id == authorization.organization_id,
                        User.role == UserRole.EMPLOYEE,
                    )
                    .correlate(Task)
                    .exists(),
            )
        )
    if authorization.role is UserRole.EMPLOYEE:
        statement = statement.where(
            Task.assigned_to_user_id == authorization.user_id,
            select(ClientAssignment.id)
            .where(
                ClientAssignment.organization_id == authorization.organization_id,
                ClientAssignment.client_id == Task.client_id,
                ClientAssignment.user_id == authorization.user_id,
            )
            .exists(),
        )
    return statement


async def task_options(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
) -> TaskOptions:
    departments = await list_departments(session, authorization=authorization)
    allowed_ids = {d.id for d in departments}
    individual = authorization.organization_mode is OrganizationMode.INDIVIDUAL
    statement = (
        select(User)
        .options(selectinload(User.department_memberships))
        .where(
            User.organization_id == authorization.organization_id,
            User.status == UserStatus.ACTIVE,
            or_(
                User.role.in_([UserRole.OWNER, UserRole.ADMIN]),
                select(ClientAssignment.id)
                .where(
                    ClientAssignment.organization_id == authorization.organization_id,
                    ClientAssignment.client_id == client_id,
                    ClientAssignment.user_id == User.id,
                )
                .exists(),
            ),
        )
    )
    if individual or authorization.role is UserRole.EMPLOYEE:
        statement = statement.where(User.id == authorization.user_id)
    elif not authorization.is_owner:
        statement = statement.where(
            or_(User.id == authorization.user_id, User.role == UserRole.EMPLOYEE)
        )
    candidates = []
    for user in await session.scalars(statement.order_by(User.full_name, User.id)):
        ids = (
            allowed_ids
            if user.role is UserRole.OWNER
            else allowed_ids & {m.department_id for m in user.department_memberships}
        )
        if individual or ids:
            candidates.append(
                TaskCandidate(id=user.id, name=user.full_name, department_ids=sorted(ids))
            )
    return TaskOptions(
        departments=[TaskDepartment(id=d.id, name=d.name) for d in departments],
        candidates=candidates,
        individual=individual,
    )


async def list_tasks(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID | None = None,
    status: TaskStatus | None = None,
    offset: int = 0,
    limit: int = 20,
) -> TaskPage:
    statement = _visible(authorization)
    options = None
    if client_id is not None:
        await get_client(session, authorization=authorization, client_id=client_id)
        statement = statement.where(Task.client_id == client_id)
        options = await task_options(session, authorization, client_id)
    else:
        statement = statement.where(Task.assigned_to_user_id == authorization.user_id)
    if status is not None:
        statement = statement.where(Task.status == status.value)
    rows = (
        await session.execute(
            statement.add_columns(Client.name, User.full_name, Department.name)
            .join(Client, Client.id == Task.client_id)
            .join(User, User.id == Task.assigned_to_user_id)
            .outerjoin(Department, Department.id == Task.department_id)
            .order_by(
                (Task.status == TaskStatus.PENDING.value).desc(),
                Task.due_at.asc().nulls_last(),
                Task.created_at.desc(),
                Task.id.desc(),
            )
            .offset(offset)
            .limit(limit + 1)
        )
    ).all()
    return TaskPage(
        items=[
            TaskResponse(
                id=t.id,
                client_id=t.client_id,
                client_name=client_name,
                assigned_to_user_id=t.assigned_to_user_id,
                assigned_to_name=assignee,
                created_by_user_id=t.created_by_user_id,
                department_id=t.department_id,
                department_name=department_name,
                title=t.title,
                description=t.description,
                due_at=t.due_at,
                status=TaskStatus(t.status),
                completed_at=t.completed_at,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t, client_name, assignee, department_name in rows[:limit]
        ],
        has_more=len(rows) > limit,
        options=options,
    )


async def _target(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
    user_id: UUID,
    department_id: UUID | None,
) -> None:
    user = await session.scalar(
        select(User)
        .where(
            User.id == user_id,
            User.organization_id == authorization.organization_id,
        )
        .with_for_update()
    )
    if user is None:
        raise ResourceNotFoundError("Assignee not found")
    options = await task_options(session, authorization, client_id)
    candidate = next((u for u in options.candidates if u.id == user_id), None)
    if candidate is None or (
        not options.individual and department_id not in candidate.department_ids
    ):
        raise AuthorizationDeniedError(
            "Assignee is inactive, outside scope or has no client access"
        )


async def create_task(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    payload: TaskRequest,
) -> Task:
    await lock_accessible_client(session, authorization, client_id)
    options = await task_options(session, authorization, client_id)
    department_id = payload.department_id
    if options.individual:
        if department_id is not None:
            raise AuthorizationDeniedError("Individual tasks have no department")
    else:
        if department_id is None and len(options.departments) == 1:
            department_id = options.departments[0].id
        if department_id is None:
            raise ResourceConflictError("Choose an available department")
        if department_id not in {d.id for d in options.departments}:
            raise AuthorizationDeniedError("Department outside scope")
        if (
            await session.scalar(
                select(Department.id)
                .where(
                    Department.id == department_id,
                    Department.organization_id == authorization.organization_id,
                )
                .with_for_update(read=True)
            )
            is None
        ):
            raise ResourceNotFoundError("Department no longer exists")
    target_id = payload.assigned_to_user_id or authorization.user_id
    await _target(session, authorization, client_id, target_id, department_id)
    if not can_manage_task(
        authorization,
        organization_id=authorization.organization_id,
        department_id=department_id,
        is_assigned_to_actor=target_id == authorization.user_id,
        is_client_assigned=True,
    ):
        raise AuthorizationDeniedError("Task creation is not allowed")
    task = Task(
        organization_id=authorization.organization_id,
        client_id=client_id,
        department_id=department_id,
        assigned_to_user_id=target_id,
        created_by_user_id=authorization.user_id,
        title=payload.title,
        description=payload.description or None,
        due_at=payload.due_at,
    )
    session.add(task)
    await session.flush()
    _audit(session, authorization, task, "CREATED_TASK", [])
    return task


async def _managed_task(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
    task_id: UUID,
) -> Task:
    await lock_accessible_client(session, authorization, client_id)
    task = await session.scalar(
        _visible(authorization)
        .where(Task.id == task_id, Task.client_id == client_id)
        .with_for_update()
    )
    if task is None:
        raise ResourceNotFoundError("Task not found")
    if not can_manage_task(
        authorization,
        organization_id=task.organization_id,
        department_id=task.department_id,
        is_assigned_to_actor=task.assigned_to_user_id == authorization.user_id,
        is_client_assigned=True,
    ):
        raise AuthorizationDeniedError("Task management is not allowed")
    return task


async def update_task(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    task_id: UUID,
    payload: TaskUpdate,
) -> None:
    task = await _managed_task(session, authorization, client_id, task_id)
    if task.status != TaskStatus.PENDING.value:
        raise ResourceConflictError("Completed tasks cannot be edited")
    target_id = payload.assigned_to_user_id or task.assigned_to_user_id
    if target_id != task.assigned_to_user_id:
        await _target(session, authorization, client_id, target_id, task.department_id)
    values = dict(
        title=payload.title,
        description=payload.description or None,
        due_at=payload.due_at,
        assigned_to_user_id=target_id,
    )
    changed = [k for k, v in values.items() if getattr(task, k) != v]
    previous_id = task.assigned_to_user_id
    for key, value in values.items():
        setattr(task, key, value)
    if changed:
        await session.flush()
        _audit(session, authorization, task, "UPDATED_TASK", changed)
        if target_id != previous_id:
            _audit(
                session,
                authorization,
                task,
                "REASSIGNED_TASK",
                ["assigned_to_user_id"],
                previous_id,
            )


async def complete_task(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    task_id: UUID,
) -> None:
    task = await _managed_task(session, authorization, client_id, task_id)
    if task.status == TaskStatus.COMPLETED.value:
        return
    task.status = TaskStatus.COMPLETED.value
    task.completed_at = datetime.now(UTC)
    await session.flush()
    _audit(session, authorization, task, "COMPLETED_TASK", ["status", "completed_at"])


def _audit(
    session: AsyncSession,
    authorization: AuthorizationContext,
    task: Task,
    action: str,
    fields: list[str],
    previous_assignee: UUID | None = None,
) -> None:
    add_audit_event(
        session,
        organization_id=task.organization_id,
        actor_user_id=authorization.user_id,
        action=action,
        entity_type="TASK",
        entity_id=task.id,
        event_data={
            "client_id": str(task.client_id),
            "assigned_to_user_id": str(task.assigned_to_user_id),
            "department_id": str(task.department_id) if task.department_id else None,
            "changed_fields": fields,
            "previous_assigned_to_user_id": str(previous_assignee) if previous_assignee else None,
        },
    )
