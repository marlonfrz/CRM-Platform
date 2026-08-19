from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrganizationMode, UserRole, UserStatus
from app.schemas.common import DepartmentName, OrganizationName, PersonName


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    mode: OrganizationMode


class UpdateOrganizationRequest(BaseModel):
    name: OrganizationName


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class DepartmentRequest(BaseModel):
    name: DepartmentName


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    department_ids: list[UUID]


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: PersonName
    role: UserRole
    department_ids: list[UUID]


class UpdateUserRequest(BaseModel):
    full_name: PersonName
    role: UserRole
    department_ids: list[UUID]
