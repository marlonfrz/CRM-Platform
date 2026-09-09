import json
from datetime import datetime
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
    "status",
    "completed_at",
]


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
    department_ids: Annotated[list[UUID], Field(max_length=100)] | None = None
    previous_department_ids: Annotated[list[UUID], Field(max_length=100)] | None = None
    changed_fields: Annotated[list[ChangedField], Field(max_length=20)] | None = None


EVENT_FIELDS: dict[str, tuple[str, set[str]]] = {
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
    "CREATED_ACTIVITY": ("ACTIVITY", {"client_id", "user_id", "department_id", "changed_fields"}),
    "UPDATED_ACTIVITY": ("ACTIVITY", {"client_id", "user_id", "department_id", "changed_fields"}),
    "CREATED_TASK": (
        "TASK",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
    ),
    "UPDATED_TASK": (
        "TASK",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
    ),
    "COMPLETED_TASK": (
        "TASK",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
    ),
    "REASSIGNED_TASK": (
        "TASK",
        {
            "client_id",
            "assigned_to_user_id",
            "department_id",
            "changed_fields",
            "previous_assigned_to_user_id",
        },
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
    created_at: datetime
    metadata: dict[str, Any]


class AuditPage(BaseModel):
    items: list[AuditEntry]
    has_more: bool
