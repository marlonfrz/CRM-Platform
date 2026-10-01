from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.activity import ActivityStatus
from app.models.activity_schedule import MonthlyMode, RecurrenceUnit

Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
NextAction = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class LegacyActivityType(StrEnum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    MEETING = "MEETING"
    NOTE = "NOTE"
    INCIDENT = "INCIDENT"
    OTHER = "OTHER"


class ActivityPeriod(StrEnum):
    TODAY = "TODAY"
    SCHEDULED = "SCHEDULED"
    HISTORY = "HISTORY"


class RecurrenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repeat_unit: RecurrenceUnit
    repeat_interval: int = Field(default=1, ge=1, le=365)
    weekdays: list[int] = Field(default_factory=list, max_length=7)
    monthly_mode: MonthlyMode | None = None
    monthly_day: int | None = Field(default=None, ge=1, le=31)
    monthly_week: int | None = Field(default=None, ge=1, le=5)
    monthly_weekday: int | None = Field(default=None, ge=0, le=6)
    ends_on: date | None = None

    @model_validator(mode="after")
    def validate_rule(self) -> Self:
        if any(day < 0 or day > 6 for day in self.weekdays) or len(set(self.weekdays)) != len(
            self.weekdays
        ):
            raise ValueError("Weekdays must be unique values from 0 to 6")
        if self.repeat_unit is RecurrenceUnit.WEEK and not self.weekdays:
            raise ValueError("Weekly recurrence requires at least one weekday")
        if self.repeat_unit is RecurrenceUnit.MONTH:
            if self.monthly_mode is MonthlyMode.DAY_OF_MONTH and self.monthly_day is None:
                raise ValueError("Monthly day is required")
            if self.monthly_mode is MonthlyMode.NTH_WEEKDAY and (
                self.monthly_week is None or self.monthly_weekday is None
            ):
                raise ValueError("Monthly week and weekday are required")
            if self.monthly_mode is None:
                raise ValueError("Monthly mode is required")
        return self


class ActivityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity_type_id: UUID | None = None
    type: LegacyActivityType | None = None
    title: Title | None = None
    description: Description
    next_action: NextAction | None = None
    scheduled_for: date = Field(default_factory=date.today)
    due_at: AwareDatetime | None = None
    occurred_at: AwareDatetime | None = None
    status: ActivityStatus = ActivityStatus.COMPLETED
    assigned_to_user_id: UUID | None = None
    department_id: UUID | None = None
    recurrence: RecurrenceRequest | None = None

    @model_validator(mode="after")
    def validate_recurrence(self) -> Self:
        if self.due_at is not None:
            self.scheduled_for = self.due_at.date()
        if self.activity_type_id is None and self.type is None:
            raise ValueError("Activity type is required")
        if self.recurrence is not None and self.status is not ActivityStatus.PENDING:
            raise ValueError("Only pending activities can be recurrent")
        if (
            self.recurrence
            and self.recurrence.ends_on is not None
            and self.recurrence.ends_on < self.scheduled_for
        ):
            raise ValueError("Recurrence end cannot precede the first activity")
        return self


class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity_type_id: UUID | None = None
    type: LegacyActivityType | None = None
    title: Title | None = None
    description: Description
    next_action: NextAction | None = None
    scheduled_for: date | None = None
    due_at: AwareDatetime | None = None
    occurred_at: AwareDatetime | None = None
    assigned_to_user_id: UUID | None = None

    @model_validator(mode="after")
    def validate_type(self) -> Self:
        if self.due_at is not None:
            self.scheduled_for = self.due_at.date()
        if self.activity_type_id is None and self.type is None:
            raise ValueError("Activity type is required")
        return self


class ActivityTypeOption(BaseModel):
    id: UUID
    name: str
    department_id: UUID | None


class ActivityTypeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    department_id: UUID | None = None


class ActivityCandidate(BaseModel):
    id: UUID
    name: str
    department_ids: list[UUID]


class ActivityResponse(BaseModel):
    id: UUID
    client_id: UUID
    user_id: UUID
    user_name: str
    assigned_to_user_id: UUID
    assigned_to_name: str
    department_id: UUID | None
    department_name: str | None
    activity_type_id: UUID
    activity_type_name: str
    type: str
    title: str | None
    description: str
    next_action: str | None
    scheduled_for: date
    status: ActivityStatus
    occurred_at: datetime | None
    completed_at: datetime | None
    schedule_id: UUID | None
    created_at: datetime
    updated_at: datetime
    can_edit: bool
    can_delete: bool


class ActivityDepartment(BaseModel):
    id: UUID
    name: str


class ActivityPage(BaseModel):
    items: list[ActivityResponse]
    departments: list[ActivityDepartment]
    candidates: list[ActivityCandidate]
    activity_types: list[ActivityTypeOption]
    can_create: bool
    can_manage_types: bool
    has_more: bool


DeleteScope = Literal["THIS", "THIS_AND_FOLLOWING"]
