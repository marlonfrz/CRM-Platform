from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class HistoryEntry(BaseModel):
    id: UUID
    kind: Literal["ACTIVITY", "TASK"]
    client_id: UUID
    client_name: str
    department_id: UUID | None
    department_name: str | None
    person_id: UUID
    person_name: str
    type: str
    title: str
    description: str | None
    next_action: str | None
    occurred_at: datetime
    due_at: datetime | None


class HistoryPage(BaseModel):
    items: list[HistoryEntry]
    has_more: bool


class DashboardMetrics(BaseModel):
    clients: int
    pending_tasks: int
    completed_tasks: int
    activities: int
    active_users: int | None
    departments: int | None


class DepartmentOverview(BaseModel):
    id: UUID
    name: str
    active_employees: int
    activities: int
    pending_tasks: int


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    departments: list[DepartmentOverview]
    recent_activities: list[HistoryEntry]
    pending_tasks: list[HistoryEntry]
