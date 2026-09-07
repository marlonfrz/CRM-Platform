from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKeyConstraint, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class ClientAssignment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "client_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_client_assignments_client",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_client_assignments_user",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assigned_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_client_assignments_actor",
        ),
        UniqueConstraint("client_id", "user_id", name="uq_client_assignments_client_user"),
        Index("ix_client_assignments_organization_user", "organization_id", "user_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    client_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    assigned_by_user_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
