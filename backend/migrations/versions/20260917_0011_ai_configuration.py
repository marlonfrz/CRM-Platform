"""Add per-organization AI configuration.

Revision ID: 20260917_0011
Revises: 20260916_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260917_0011"
down_revision: str | None = "20260916_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_configurations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "provider IN ('disabled', 'ollama', 'openai', 'anthropic', 'gemini')",
            name=op.f("ck_ai_configurations_provider"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_configurations_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("organization_id", name=op.f("pk_ai_configurations")),
    )


def downgrade() -> None:
    op.drop_table("ai_configurations")
