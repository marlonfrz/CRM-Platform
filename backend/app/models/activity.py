from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ActivityType(StrEnum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    MEETING = "MEETING"
    NOTE = "NOTE"
    INCIDENT = "INCIDENT"
    OTHER = "OTHER"


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
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_activities_department",
        ),
        CheckConstraint(
            "type IN ('CALL', 'EMAIL', 'MEETING', 'NOTE', 'INCIDENT', 'OTHER')",
            name="activity_type",
        ),
        CheckConstraint("length(trim(description)) > 0", name="activity_description"),
        Index("ix_activities_client_date", "organization_id", "client_id", "occurred_at", "id"),
        Index("ix_activities_department", "organization_id", "department_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    client_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    next_action: Mapped[str | None] = mapped_column(String(2000))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
