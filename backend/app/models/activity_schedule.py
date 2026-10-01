from datetime import date
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RecurrenceUnit(StrEnum):
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"


class MonthlyMode(StrEnum):
    DAY_OF_MONTH = "DAY_OF_MONTH"
    NTH_WEEKDAY = "NTH_WEEKDAY"


class ActivitySchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_schedules"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "id", name="uq_activity_schedules_organization_id_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_activity_schedules_client",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_activity_schedules_creator",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assigned_to_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_activity_schedules_assignee",
        ),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_activity_schedules_department",
        ),
        ForeignKeyConstraint(
            ["organization_id", "activity_type_id"],
            ["activity_types.organization_id", "activity_types.id"],
            name="fk_activity_schedules_activity_type",
        ),
        CheckConstraint("repeat_unit IN ('DAY', 'WEEK', 'MONTH')", name="repeat_unit"),
        CheckConstraint("repeat_interval > 0", name="repeat_interval"),
        CheckConstraint(
            "monthly_mode IS NULL OR monthly_mode IN ('DAY_OF_MONTH', 'NTH_WEEKDAY')",
            name="monthly_mode",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    client_id: Mapped[UUID] = mapped_column(nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(nullable=False)
    assigned_to_user_id: Mapped[UUID] = mapped_column(nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(nullable=True)
    activity_type_id: Mapped[UUID] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    next_action: Mapped[str | None] = mapped_column(String(2000))
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    repeat_unit: Mapped[str] = mapped_column(String(10), nullable=False)
    repeat_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    weekdays: Mapped[str | None] = mapped_column(String(20))
    monthly_mode: Mapped[str | None] = mapped_column(String(20))
    monthly_day: Mapped[int | None] = mapped_column(Integer)
    monthly_week: Mapped[int | None] = mapped_column(Integer)
    monthly_weekday: Mapped[int | None] = mapped_column(Integer)
    ends_on: Mapped[date | None] = mapped_column(Date)
    last_materialized_on: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
