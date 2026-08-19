from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import OrganizationMode, UserRole


class DepartmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class WorkspaceResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    organization_mode: OrganizationMode
    user_id: UUID
    user_name: str
    user_email: str
    user_role: UserRole
    departments: list[DepartmentSummary]
