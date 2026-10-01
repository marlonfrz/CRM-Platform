from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ActivityStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class Activity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_activities_client",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_activities_user",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assigned_to_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_activities_assignee",
        ),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_activities_department",
        ),
        ForeignKeyConstraint(
            ["organization_id", "activity_type_id"],
            ["activity_types.organization_id", "activity_types.id"],
            name="fk_activities_activity_type",
        ),
        ForeignKeyConstraint(
            ["organization_id", "schedule_id"],
            ["activity_schedules.organization_id", "activity_schedules.id"],
            name="fk_activities_schedule",
        ),
        CheckConstraint("status IN ('PENDING', 'COMPLETED')", name="activity_status"),
        CheckConstraint("length(trim(description)) > 0", name="activity_description"),
        CheckConstraint(
            "(status = 'PENDING' AND occurred_at IS NULL AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND occurred_at IS NOT NULL AND completed_at IS NOT NULL)",
            name="activity_completion",
        ),
        UniqueConstraint(
            "schedule_id", "scheduled_for", name="uq_activities_schedule_date"
        ),
        Index(
            "ix_activities_client_date",
            "organization_id",
            "client_id",
            "scheduled_for",
            "id",
        ),
        Index(
            "ix_activities_client_status",
            "organization_id",
            "client_id",
            "status",
            "scheduled_for",
        ),
        Index(
            "ix_activities_assignee",
            "organization_id",
            "assigned_to_user_id",
            "status",
            "scheduled_for",
        ),
        Index("ix_activities_department", "organization_id", "department_id"),
        Index("ix_activities_type", "organization_id", "activity_type_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    client_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    created_by_user_id: Mapped[UUID] = synonym("user_id")
    assigned_to_user_id: Mapped[UUID] = mapped_column(nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(nullable=True)
    activity_type_id: Mapped[UUID] = mapped_column(nullable=False)
    schedule_id: Mapped[UUID | None] = mapped_column(nullable=True)
    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    next_action: Mapped[str | None] = mapped_column(String(2000))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ActivityStatus.COMPLETED.value
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
