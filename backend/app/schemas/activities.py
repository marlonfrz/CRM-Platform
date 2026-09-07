from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from app.models.activity import ActivityType

Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]
NextAction = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class ActivityCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: ActivityType
    description: Description
    next_action: NextAction | None = None
    occurred_at: AwareDatetime


class ActivityRequest(ActivityCorrection):
    department_id: UUID | None = None


class ActivityResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    department_id: UUID | None
    department_name: str | None
    type: ActivityType
    description: str
    next_action: str | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime
    can_edit: bool


class ActivityDepartment(BaseModel):
    id: UUID
    name: str


class ActivityPage(BaseModel):
    items: list[ActivityResponse]
    departments: list[ActivityDepartment]
    can_create: bool
    has_more: bool
