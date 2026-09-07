from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class Client(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_clients_organization_id_id"),
        CheckConstraint("btrim(name) <> ''", name="name_not_blank"),
        Index("ix_clients_organization_id_name", "organization_id", "name"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    organization: Mapped[Organization] = relationship(back_populates="clients")
    contacts: Mapped[list[ClientContact]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="ClientContact.full_name",
    )


class ClientContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "client_contacts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            ondelete="CASCADE",
            name="fk_client_contacts_client",
        ),
        CheckConstraint("btrim(full_name) <> ''", name="full_name_not_blank"),
        CheckConstraint("email IS NULL OR email = lower(email)", name="email_normalized"),
        Index("ix_client_contacts_organization_id_client_id", "organization_id", "client_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[UUID] = mapped_column(nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

    client: Mapped[Client] = relationship(back_populates="contacts")
