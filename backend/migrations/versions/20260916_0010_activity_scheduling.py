"""Add unified activity scheduling and configurable types.

Revision ID: 20260916_0010
Revises: 20260914_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260916_0010"
down_revision: str | None = "20260914_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activity_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_types")),
        sa.UniqueConstraint("organization_id", "id", name="uq_activity_types_organization_id_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name=op.f("fk_activity_types_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            ondelete="CASCADE",
            name="fk_activity_types_department",
        ),
    )
    op.create_index(
        "ix_activity_types_scope",
        "activity_types",
        ["organization_id", "department_id", "normalized_name"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.execute(
        "INSERT INTO activity_types "
        "(id, organization_id, department_id, name, normalized_name, is_active) "
        "SELECT gen_random_uuid(), organizations.id, NULL, defaults.name, "
        "defaults.normalized_name, true "
        "FROM organizations CROSS JOIN (VALUES "
        "('Llamada', 'llamada'), ('Email', 'email'), ('Reunión', 'reunión'), "
        "('Nota', 'nota'), ('Incidencia', 'incidencia'), ('Otro', 'otro')"
        ") AS defaults(name, normalized_name)"
    )

    op.create_table(
        "activity_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("activity_type_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("next_action", sa.String(2000), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("repeat_unit", sa.String(10), nullable=False),
        sa.Column("repeat_interval", sa.Integer(), nullable=False),
        sa.Column("weekdays", sa.String(20), nullable=True),
        sa.Column("monthly_mode", sa.String(20), nullable=True),
        sa.Column("monthly_day", sa.Integer(), nullable=True),
        sa.Column("monthly_week", sa.Integer(), nullable=True),
        sa.Column("monthly_weekday", sa.Integer(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("last_materialized_on", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_schedules")),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_activity_schedules_organization_id_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "client_id"],
            ["clients.organization_id", "clients.id"],
            name="fk_activity_schedules_client",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_activity_schedules_creator",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assigned_to_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_activity_schedules_assignee",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_activity_schedules_department",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "activity_type_id"],
            ["activity_types.organization_id", "activity_types.id"],
            name="fk_activity_schedules_activity_type",
        ),
        sa.CheckConstraint(
            "repeat_unit IN ('DAY', 'WEEK', 'MONTH')",
            name=op.f("ck_activity_schedules_repeat_unit"),
        ),
        sa.CheckConstraint(
            "repeat_interval > 0", name=op.f("ck_activity_schedules_repeat_interval")
        ),
        sa.CheckConstraint(
            "monthly_mode IS NULL OR monthly_mode IN ('DAY_OF_MONTH', 'NTH_WEEKDAY')",
            name=op.f("ck_activity_schedules_monthly_mode"),
        ),
    )

    op.add_column("activities", sa.Column("activity_type_id", sa.Uuid(), nullable=True))
    op.add_column("activities", sa.Column("schedule_id", sa.Uuid(), nullable=True))
    op.add_column("activities", sa.Column("scheduled_for", sa.Date(), nullable=True))
    op.execute(
        "UPDATE activities SET activity_type_id = activity_types.id "
        "FROM activity_types WHERE activity_types.organization_id = activities.organization_id "
        "AND activity_types.department_id IS NULL "
        "AND activity_types.normalized_name = CASE activities.type "
        "WHEN 'CALL' THEN 'llamada' WHEN 'EMAIL' THEN 'email' WHEN 'MEETING' THEN 'reunión' "
        "WHEN 'NOTE' THEN 'nota' WHEN 'INCIDENT' THEN 'incidencia' ELSE 'otro' END"
    )
    op.execute(
        "UPDATE activities SET scheduled_for = "
        "COALESCE(due_at::date, occurred_at::date, created_at::date)"
    )
    op.alter_column("activities", "activity_type_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("activities", "scheduled_for", existing_type=sa.Date(), nullable=False)
    op.create_foreign_key(
        "fk_activities_activity_type",
        "activities",
        "activity_types",
        ["organization_id", "activity_type_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_activities_schedule",
        "activities",
        "activity_schedules",
        ["organization_id", "schedule_id"],
        ["organization_id", "id"],
    )
    op.create_unique_constraint(
        "uq_activities_schedule_date", "activities", ["schedule_id", "scheduled_for"]
    )
    op.drop_index("ix_activities_assignee", table_name="activities")
    op.drop_index("ix_activities_client_status", table_name="activities")
    op.drop_index("ix_activities_client_date", table_name="activities")
    op.drop_constraint(op.f("ck_activities_activity_category"), "activities", type_="check")
    op.drop_column("activities", "category")
    op.drop_column("activities", "type")
    op.drop_column("activities", "due_at")
    op.create_index(
        "ix_activities_client_date",
        "activities",
        ["organization_id", "client_id", "scheduled_for", "id"],
    )
    op.create_index(
        "ix_activities_client_status",
        "activities",
        ["organization_id", "client_id", "status", "scheduled_for"],
    )
    op.create_index(
        "ix_activities_assignee",
        "activities",
        ["organization_id", "assigned_to_user_id", "status", "scheduled_for"],
    )
    op.create_index("ix_activities_type", "activities", ["organization_id", "activity_type_id"])
    op.execute("UPDATE audit_logs SET entity_type = 'ACTIVITY' WHERE entity_type = 'TASK'")


def downgrade() -> None:
    op.execute(
        "UPDATE audit_logs SET entity_type = 'TASK' "
        "WHERE action IN ('CREATED_TASK', 'UPDATED_TASK', "
        "'COMPLETED_TASK', 'REASSIGNED_TASK')"
    )
    op.add_column("activities", sa.Column("category", sa.String(20), nullable=True))
    op.add_column("activities", sa.Column("type", sa.String(20), nullable=True))
    op.add_column("activities", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE activities SET category = CASE WHEN title IS NULL THEN 'ACTIVITY' ELSE 'TASK' END, "
        "type = CASE activity_types.normalized_name WHEN 'llamada' THEN 'CALL' "
        "WHEN 'email' THEN 'EMAIL' WHEN 'reunión' THEN 'MEETING' WHEN 'nota' THEN 'NOTE' "
        "WHEN 'incidencia' THEN 'INCIDENT' ELSE 'OTHER' END, "
        "due_at = scheduled_for::timestamp with time zone FROM activity_types "
        "WHERE activity_types.id = activities.activity_type_id"
    )
    op.alter_column("activities", "category", existing_type=sa.String(20), nullable=False)
    op.alter_column("activities", "type", existing_type=sa.String(20), nullable=False)
    op.create_check_constraint(
        op.f("ck_activities_activity_category"),
        "activities",
        "category IN ('ACTIVITY', 'TASK')",
    )
    op.drop_index("ix_activities_type", table_name="activities")
    op.drop_index("ix_activities_assignee", table_name="activities")
    op.drop_index("ix_activities_client_status", table_name="activities")
    op.drop_index("ix_activities_client_date", table_name="activities")
    op.create_index(
        "ix_activities_client_date",
        "activities",
        ["organization_id", "client_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_activities_client_status",
        "activities",
        ["organization_id", "client_id", "status", "due_at"],
    )
    op.create_index(
        "ix_activities_assignee",
        "activities",
        ["organization_id", "assigned_to_user_id", "status", "due_at"],
    )
    op.drop_constraint("uq_activities_schedule_date", "activities", type_="unique")
    op.drop_constraint("fk_activities_schedule", "activities", type_="foreignkey")
    op.drop_constraint("fk_activities_activity_type", "activities", type_="foreignkey")
    op.drop_column("activities", "scheduled_for")
    op.drop_column("activities", "schedule_id")
    op.drop_column("activities", "activity_type_id")
    op.drop_table("activity_schedules")
    op.drop_index("ix_activity_types_scope", table_name="activity_types")
    op.drop_table("activity_types")
