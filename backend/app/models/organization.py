from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OrganizationMode
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.department import Department
    from app.models.user import User


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[OrganizationMode] = mapped_column(
        Enum(OrganizationMode, name="organization_mode"), nullable=False
    )

    users: Mapped[list[User]] = relationship(back_populates="organization")
    departments: Mapped[list[Department]] = relationship(back_populates="organization")
    clients: Mapped[list[Client]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
