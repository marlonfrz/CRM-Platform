from uuid import UUID, uuid5

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

ACTIVITY_TYPE_NAMESPACE = UUID("54e2ff39-f3e8-4a1c-8892-73f26ccb799e")


def activity_type_identifier(organization_id: UUID, normalized_name: str) -> UUID:
    return uuid5(ACTIVITY_TYPE_NAMESPACE, f"{organization_id}:{normalized_name}")


class ActivityType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_types"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_activity_types_organization_id_id"),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            ondelete="CASCADE",
            name="fk_activity_types_department",
        ),
        Index(
            "ix_activity_types_scope",
            "organization_id",
            "department_id",
            "normalized_name",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[UUID | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
