"""Add short-lived AI summary cache.

Revision ID: 20260918_0012
Revises: 20260917_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260918_0012"
down_revision: str | None = "20260917_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_summary_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("context_sha256", sa.String(64), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_summary_cache_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_summary_cache")),
        sa.UniqueConstraint(
            "organization_id",
            "provider",
            "model",
            "context_sha256",
            name=op.f("uq_ai_summary_cache_identity"),
        ),
    )
    op.create_index(
        "ix_ai_summary_cache_expires_at", "ai_summary_cache", ["expires_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_ai_summary_cache_expires_at", table_name="ai_summary_cache")
    op.drop_table("ai_summary_cache")
