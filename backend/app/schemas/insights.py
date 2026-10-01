from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.activity import ActivityStatus


class HistoryEntry(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    department_id: UUID | None
    department_name: str | None
    person_id: UUID
    person_name: str
    activity_type_id: UUID
    activity_type_name: str
    title: str | None
    description: str
    next_action: str | None
    scheduled_for: date
    status: ActivityStatus
    occurred_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    schedule_id: UUID | None
    can_edit: bool = False
    can_delete: bool = False


class HistoryPage(BaseModel):
    items: list[HistoryEntry]
    has_more: bool


class DashboardMetrics(BaseModel):
    clients: int
    pending_tasks: int
    completed_tasks: int
    activities: int
    today_clients: int
    today_activities: int
    today_pending_tasks: int
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
    today_activities: list[HistoryEntry]
    recent_activities: list[HistoryEntry]
    pending_tasks: list[HistoryEntry]
