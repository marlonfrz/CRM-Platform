from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class Department(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_departments_organization_id_id"),
        UniqueConstraint(
            "organization_id", "normalized_name", name="uq_departments_organization_id_name"
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="departments")
    members: Mapped[list[DepartmentMember]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
        overlaps="department_memberships,user",
    )


class DepartmentMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "department_members"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            ondelete="CASCADE",
            name="fk_department_members_department",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            ondelete="CASCADE",
            name="fk_department_members_user",
        ),
        UniqueConstraint(
            "organization_id",
            "department_id",
            "user_id",
            name="uq_department_members_department_user",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    department_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)

    department: Mapped[Department] = relationship(
        back_populates="members", overlaps="department_memberships,user"
    )
    user: Mapped[User] = relationship(
        back_populates="department_memberships", overlaps="department,members"
    )
