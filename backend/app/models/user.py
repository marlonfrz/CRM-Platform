from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole, UserStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.department import DepartmentMember
    from app.models.organization import Organization
    from app.models.session import UserSession


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_users_organization_id_id"),
        UniqueConstraint("organization_id", "email", name="uq_users_organization_id_email"),
        CheckConstraint("email = lower(email)", name="email_normalized"),
        CheckConstraint(
            "status != 'ACTIVE' OR password_hash IS NOT NULL", name="active_user_has_password"
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), nullable=False, default=UserStatus.PENDING
    )

    organization: Mapped[Organization] = relationship(back_populates="users")
    department_memberships: Mapped[list[DepartmentMember]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        overlaps="department,members",
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
