from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.db.dependencies import get_db_session
from app.models.activity import ActivityStatus
from app.policies.authorization import AuthorizationContext
from app.schemas.tasks import TaskPage, TaskRequest, TaskUpdate
from app.services.exceptions import DomainError
from app.services.tasks import complete_task, create_task, list_tasks, update_task

from .errors import domain_http_exception

router = APIRouter(tags=["tasks"])
Authorization = Annotated[AuthorizationContext, Depends(get_authorization_context)]
Database = Annotated[AsyncSession, Depends(get_db_session)]
Csrf = Annotated[Principal, Depends(require_csrf)]
Offset = Annotated[int, Query(ge=0, le=100000)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/tasks/mine", response_model=TaskPage)
async def get_my_tasks(
    authorization: Authorization,
    session: Database,
    status: ActivityStatus | None = None,
    offset: Offset = 0,
    limit: Limit = 20,
) -> TaskPage:
    return await list_tasks(
        session, authorization=authorization, status=status, offset=offset, limit=limit
    )


@router.get("/clients/{client_id}/tasks", response_model=TaskPage)
async def get_client_tasks(
    client_id: UUID,
    authorization: Authorization,
    session: Database,
    status: ActivityStatus | None = None,
    offset: Offset = 0,
    limit: Limit = 20,
) -> TaskPage:
    try:
        return await list_tasks(
            session,
            authorization=authorization,
            client_id=client_id,
            status=status,
            offset=offset,
            limit=limit,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.post("/clients/{client_id}/tasks", status_code=status.HTTP_201_CREATED)
async def post_task(
    client_id: UUID, payload: TaskRequest, _: Csrf, authorization: Authorization, session: Database
) -> dict[str, UUID]:
    try:
        task = await create_task(
            session, authorization=authorization, client_id=client_id, payload=payload
        )
        return {"id": task.id}
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.patch("/clients/{client_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def patch_task(
    client_id: UUID,
    task_id: UUID,
    payload: TaskUpdate,
    _: Csrf,
    authorization: Authorization,
    session: Database,
) -> None:
    try:
        await update_task(
            session,
            authorization=authorization,
            client_id=client_id,
            task_id=task_id,
            payload=payload,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.post(
    "/clients/{client_id}/tasks/{task_id}/complete", status_code=status.HTTP_204_NO_CONTENT
)
async def post_complete_task(
    client_id: UUID, task_id: UUID, _: Csrf, authorization: Authorization, session: Database
) -> None:
    try:
        await complete_task(
            session, authorization=authorization, client_id=client_id, task_id=task_id
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
