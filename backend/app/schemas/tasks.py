from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from app.models.task import TaskStatus

TaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
TaskDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: TaskTitle
    description: TaskDescription | None = None
    due_at: AwareDatetime | None = None
    assigned_to_user_id: UUID | None = None


class TaskRequest(TaskUpdate):
    department_id: UUID | None = None


class TaskCandidate(BaseModel):
    id: UUID
    name: str
    department_ids: list[UUID]


class TaskDepartment(BaseModel):
    id: UUID
    name: str


class TaskOptions(BaseModel):
    departments: list[TaskDepartment]
    candidates: list[TaskCandidate]
    individual: bool


class TaskResponse(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    assigned_to_user_id: UUID
    assigned_to_name: str
    created_by_user_id: UUID
    department_id: UUID | None
    department_name: str | None
    title: str
    description: str | None
    due_at: datetime | None
    status: TaskStatus
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskPage(BaseModel):
    items: list[TaskResponse]
    has_more: bool
    options: TaskOptions | None = None
