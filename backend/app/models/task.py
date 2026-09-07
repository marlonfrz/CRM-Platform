from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_tasks_client",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assigned_to_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_tasks_assignee",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_tasks_creator",
        ),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_tasks_department",
        ),
        CheckConstraint("length(trim(title)) > 0", name="task_title"),
        CheckConstraint(
            "(status = 'PENDING' AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND completed_at IS NOT NULL)",
            name="task_completion",
        ),
        Index("ix_tasks_client", "organization_id", "client_id", "status", "due_at"),
        Index("ix_tasks_assignee", "organization_id", "assigned_to_user_id", "status", "due_at"),
        Index("ix_tasks_department", "organization_id", "department_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    client_id: Mapped[UUID] = mapped_column(nullable=False)
    assigned_to_user_id: Mapped[UUID] = mapped_column(nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskStatus.PENDING.value
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
