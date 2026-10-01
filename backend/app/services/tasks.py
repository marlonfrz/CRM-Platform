"""Compatibility projection for the former task API.

All writes delegate to the unified activity service. New clients should use
``/clients/{client_id}/activities`` directly.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, ActivityType, Client, Department, User
from app.models.activity import ActivityStatus
from app.policies.authorization import AuthorizationContext
from app.schemas.activities import ActivityRequest, ActivityUpdate
from app.schemas.tasks import TaskOptions, TaskPage, TaskRequest, TaskResponse, TaskUpdate
from app.services.activities import complete_activity, create_activity, update_activity
from app.services.activity_options import activity_options
from app.services.clients import get_client
from app.services.exceptions import ResourceConflictError, ResourceNotFoundError
from app.services.scopes import visible_tasks


async def task_options(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
) -> TaskOptions:
    return await activity_options(session, authorization, client_id)


async def list_tasks(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID | None = None,
    status: ActivityStatus | None = None,
    offset: int = 0,
    limit: int = 20,
) -> TaskPage:
    statement = visible_tasks(authorization)
    options = None
    if client_id is not None:
        await get_client(session, authorization=authorization, client_id=client_id)
        statement = statement.where(Activity.client_id == client_id)
        options = await activity_options(session, authorization, client_id)
    else:
        statement = statement.where(Activity.assigned_to_user_id == authorization.user_id)
    if status is not None:
        statement = statement.where(Activity.status == status.value)
    rows = (
        await session.execute(
            statement.add_columns(Client.name, User.full_name, Department.name)
            .join(Client, Client.id == Activity.client_id)
            .join(User, User.id == Activity.assigned_to_user_id)
            .outerjoin(Department, Department.id == Activity.department_id)
            .order_by(
                (Activity.status == ActivityStatus.PENDING.value).desc(),
                Activity.scheduled_for.asc(),
                Activity.created_at.desc(),
                Activity.id.desc(),
            )
            .offset(offset)
            .limit(limit + 1)
        )
    ).all()
    return TaskPage(
        items=[
            TaskResponse(
                id=activity.id,
                client_id=activity.client_id,
                client_name=client_name,
                assigned_to_user_id=activity.assigned_to_user_id,
                assigned_to_name=assignee,
                created_by_user_id=activity.created_by_user_id,
                department_id=activity.department_id,
                department_name=department_name,
                title=activity.title or activity.description[:200],
                description=activity.description,
                due_at=activity.scheduled_for,
                status=ActivityStatus(activity.status),
                completed_at=activity.completed_at,
                created_at=activity.created_at,
                updated_at=activity.updated_at,
            )
            for activity, client_name, assignee, department_name in rows[:limit]
        ],
        has_more=len(rows) > limit,
        options=options,
    )


async def _default_type(
    session: AsyncSession, authorization: AuthorizationContext
) -> ActivityType:
    activity_type = await session.scalar(
        select(ActivityType).where(
            ActivityType.organization_id == authorization.organization_id,
            ActivityType.department_id.is_(None),
            ActivityType.normalized_name == "otro",
        )
    )
    if activity_type is None:
        raise ResourceNotFoundError("Default activity type not found")
    return activity_type


async def create_task(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    payload: TaskRequest,
) -> Activity:
    activity_type = await _default_type(session, authorization)
    activities = await create_activity(
        session,
        authorization=authorization,
        client_id=client_id,
        payload=ActivityRequest(
            activity_type_id=activity_type.id,
            title=payload.title,
            description=payload.description or payload.title,
            scheduled_for=payload.due_at.date() if payload.due_at else date.today(),
            status=ActivityStatus.PENDING,
            assigned_to_user_id=payload.assigned_to_user_id,
            department_id=payload.department_id,
        ),
    )
    return activities[0]


async def update_task(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    task_id: UUID,
    payload: TaskUpdate,
) -> None:
    await get_client(session, authorization=authorization, client_id=client_id)
    activity = await session.scalar(
        visible_tasks(authorization).where(
            Activity.id == task_id, Activity.client_id == client_id
        )
    )
    if activity is None:
        raise ResourceNotFoundError("Activity not found")
    if activity.status != ActivityStatus.PENDING.value:
        raise ResourceConflictError("Completed activities cannot be edited through the task API")
    await update_activity(
        session,
        authorization=authorization,
        client_id=client_id,
        activity_id=task_id,
        payload=ActivityUpdate(
            activity_type_id=activity.activity_type_id,
            title=payload.title,
            description=payload.description or payload.title,
            next_action=activity.next_action,
            scheduled_for=payload.due_at.date() if payload.due_at else activity.scheduled_for,
            assigned_to_user_id=payload.assigned_to_user_id,
        ),
    )


async def complete_task(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    task_id: UUID,
) -> None:
    await get_client(session, authorization=authorization, client_id=client_id)
    activity = await session.scalar(
        visible_tasks(authorization).where(
            Activity.id == task_id, Activity.client_id == client_id
        )
    )
    if activity is None:
        raise ResourceNotFoundError("Activity not found")
    await complete_activity(
        session,
        authorization=authorization,
        client_id=client_id,
        activity_id=task_id,
    )
