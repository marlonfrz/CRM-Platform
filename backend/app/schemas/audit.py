import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(max_length=200)]
Role = Literal["OWNER", "ADMIN", "EMPLOYEE"]
ChangedField = Literal[
    "name",
    "address",
    "notes",
    "full_name",
    "position",
    "email",
    "phone",
    "role",
    "department_ids",
    "type",
    "description",
    "next_action",
    "occurred_at",
    "title",
    "assigned_to_user_id",
    "due_at",
    "scheduled_for",
    "activity_type_id",
    "status",
    "completed_at",
]


class AuditCategory(StrEnum):
    ACCESS = "ACCESS"
    TEAM = "TEAM"
    CLIENTS = "CLIENTS"
    ACTIVITY = "ACTIVITY"
    ORGANIZATION = "ORGANIZATION"
    AI = "AI"


class PreviousUser(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: Name
    role: Role


class AuditMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    previous_name: Name | None = None
    full_name: Name | None = None
    previous: PreviousUser | None = None
    role: Role | None = None
    client_id: UUID | None = None
    user_id: UUID | None = None
    department_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    previous_assigned_to_user_id: UUID | None = None
    schedule_id: UUID | None = None
    department_ids: Annotated[list[UUID], Field(max_length=100)] | None = None
    previous_department_ids: Annotated[list[UUID], Field(max_length=100)] | None = None
    changed_fields: Annotated[list[ChangedField], Field(max_length=20)] | None = None
    scope: Literal[
        "CLIENT", "DEPARTMENT", "ORGANIZATION", "THIS", "THIS_AND_FOLLOWING"
    ] | None = None
    provider: Literal["disabled", "ollama", "openai", "anthropic", "gemini"] | None = None
    model: (
        Annotated[str, StringConstraints(max_length=100, pattern=r"^[a-zA-Z0-9._:/-]+$")] | None
    ) = None
    source_ids: Annotated[list[UUID], Field(max_length=50)] | None = None
    context_sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")] | None = None
    provider_called: bool | None = None
    cache_hit: bool | None = None
    error_code: (
        Literal["AI_PROVIDER_UNAVAILABLE", "AI_INVALID_OUTPUT", "AI_ACCESS_CHANGED", "AI_TIMEOUT"]
        | None
    ) = None


EVENT_FIELDS: dict[str, tuple[str, set[str]]] = {
    "UPDATED_AI_CONFIGURATION": ("AI_CONFIGURATION", {"provider", "model"}),
    "AI_SUMMARY_REQUESTED": (
        "AI_SUMMARY",
        {
            "scope",
            "provider",
            "model",
            "source_ids",
            "context_sha256",
            "client_id",
            "department_id",
            "provider_called",
        },
    ),
    "AI_SUMMARY_COMPLETED": ("AI_SUMMARY", {"cache_hit"}),
    "AI_SUMMARY_FAILED": ("AI_SUMMARY", {"error_code"}),
    "INITIALIZED_ORGANIZATION": ("ORGANIZATION", set()),
    "UPDATED_ORGANIZATION": ("ORGANIZATION", {"previous_name", "name"}),
    "AUTH_LOGIN": ("USER_SESSION", set()),
    "AUTH_LOGOUT": ("USER_SESSION", set()),
    "PASSWORD_CHANGED": ("USER", set()),
    "CREATED_USER": ("USER", {"role", "department_ids"}),
    "UPDATED_USER": (
        "USER",
        {"previous", "full_name", "role", "department_ids", "previous_department_ids"},
    ),
    "DISABLED_USER": ("USER", set()),
    "ACTIVATED_USER": ("USER", set()),
    "ACCEPTED_INVITATION": ("USER", set()),
    "RESENT_INVITATION": ("USER", set()),
    "CREATED_DEPARTMENT": ("DEPARTMENT", {"name"}),
    "UPDATED_DEPARTMENT": ("DEPARTMENT", {"previous_name", "name"}),
    "DELETED_DEPARTMENT": ("DEPARTMENT", {"name"}),
    "CREATED_CLIENT": ("CLIENT", {"name"}),
    "UPDATED_CLIENT": ("CLIENT", {"previous_name", "name", "changed_fields"}),
    "CREATED_CLIENT_CONTACT": ("CLIENT_CONTACT", {"client_id", "full_name"}),
    "UPDATED_CLIENT_CONTACT": (
        "CLIENT_CONTACT",
        {"client_id", "previous_name", "full_name", "changed_fields"},
    ),
    "DELETED_CLIENT_CONTACT": ("CLIENT_CONTACT", {"client_id", "full_name"}),
    "ASSIGNED_CLIENT": ("CLIENT_ASSIGNMENT", {"client_id", "user_id"}),
    "UNASSIGNED_CLIENT": ("CLIENT_ASSIGNMENT", {"client_id", "user_id"}),
    "CREATED_ACTIVITY": (
        "ACTIVITY",
        {
            "client_id",
            "user_id",
            "assigned_to_user_id",
            "department_id",
            "schedule_id",
            "changed_fields",
        },
    ),
    "UPDATED_ACTIVITY": (
        "ACTIVITY",
        {
            "client_id",
            "user_id",
            "assigned_to_user_id",
            "department_id",
            "schedule_id",
            "changed_fields",
        },
    ),
    "COMPLETED_ACTIVITY": (
        "ACTIVITY",
        {
            "client_id",
            "user_id",
            "assigned_to_user_id",
            "department_id",
            "schedule_id",
            "changed_fields",
        },
    ),
    "DELETED_ACTIVITY": ("ACTIVITY", {"client_id", "scope"}),
    "CREATED_TASK": (
        "ACTIVITY",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
    ),
    "UPDATED_TASK": (
        "ACTIVITY",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
    ),
    "COMPLETED_TASK": (
        "ACTIVITY",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
    ),
    "REASSIGNED_TASK": (
        "ACTIVITY",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
    ),
}

AUDIT_CATEGORY_ACTIONS: dict[AuditCategory, frozenset[str]] = {
    AuditCategory.ACCESS: frozenset({"AUTH_LOGIN", "AUTH_LOGOUT"}),
    AuditCategory.TEAM: frozenset(
        {
            "PASSWORD_CHANGED",
            "CREATED_USER",
            "UPDATED_USER",
            "DISABLED_USER",
            "ACTIVATED_USER",
            "ACCEPTED_INVITATION",
            "RESENT_INVITATION",
            "CREATED_DEPARTMENT",
            "UPDATED_DEPARTMENT",
            "DELETED_DEPARTMENT",
        }
    ),
    AuditCategory.CLIENTS: frozenset(
        {
            "CREATED_CLIENT",
            "UPDATED_CLIENT",
            "CREATED_CLIENT_CONTACT",
            "UPDATED_CLIENT_CONTACT",
            "DELETED_CLIENT_CONTACT",
            "ASSIGNED_CLIENT",
            "UNASSIGNED_CLIENT",
        }
    ),
    AuditCategory.ACTIVITY: frozenset(
        {
            "CREATED_ACTIVITY",
            "UPDATED_ACTIVITY",
            "COMPLETED_ACTIVITY",
            "DELETED_ACTIVITY",
            "CREATED_TASK",
            "UPDATED_TASK",
            "COMPLETED_TASK",
            "REASSIGNED_TASK",
        }
    ),
    AuditCategory.ORGANIZATION: frozenset(
        {"INITIALIZED_ORGANIZATION", "UPDATED_ORGANIZATION"}
    ),
    AuditCategory.AI: frozenset(
        {
            "AI_SUMMARY_REQUESTED",
            "AI_SUMMARY_COMPLETED",
            "AI_SUMMARY_FAILED",
            "UPDATED_AI_CONFIGURATION",
        }
    ),
}


def validate_metadata(action: str, entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
    contract = EVENT_FIELDS.get(action)
    if contract is None or contract[0] != entity_type or not data.keys() <= contract[1]:
        raise ValueError("Invalid audit event contract")
    clean = AuditMetadata.model_validate(data).model_dump(mode="json", exclude_unset=True)
    if len(json.dumps(clean, ensure_ascii=False).encode()) > 8192:
        raise ValueError("Audit metadata exceeds 8192 bytes")
    return clean


def readable_metadata(action: str, entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
    allowed = EVENT_FIELDS.get(action, ("", set()))[1]
    try:
        return validate_metadata(
            action, entity_type, {key: value for key, value in data.items() if key in allowed}
        )
    except ValueError:
        return {}


class AuditEntry(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: UUID
    entity_name: str | None
    created_at: datetime
    metadata: dict[str, Any]
    metadata_names: dict[str, str | list[str]]


class AuditActorOption(BaseModel):
    id: UUID
    name: str


class AuditPage(BaseModel):
    items: list[AuditEntry]
    actors: list[AuditActorOption]
    has_more: bool
