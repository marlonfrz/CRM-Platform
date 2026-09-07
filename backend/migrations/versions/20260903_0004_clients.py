"""Add global clients and contacts.

Revision ID: 20260903_0004
Revises: 20260819_0003
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_0004"
down_revision: str | None = "20260819_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(name) <> ''", name=op.f("ck_clients_name_not_blank")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_clients_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
        sa.UniqueConstraint("organization_id", "id", name="uq_clients_organization_id_id"),
    )
    op.create_index("ix_clients_organization_id_name", "clients", ["organization_id", "name"])
    op.create_table(
        "client_contacts",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("position", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email IS NULL OR email = lower(email)",
            name=op.f("ck_client_contacts_email_normalized"),
        ),
        sa.CheckConstraint(
            "btrim(full_name) <> ''", name=op.f("ck_client_contacts_full_name_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_client_contacts_client",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_client_contacts_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_contacts")),
    )
    op.create_index(
        "ix_client_contacts_organization_id_client_id",
        "client_contacts",
        ["organization_id", "client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_client_contacts_organization_id_client_id", table_name="client_contacts")
    op.drop_table("client_contacts")
    op.drop_index("ix_clients_organization_id_name", table_name="clients")
    op.drop_table("clients")
