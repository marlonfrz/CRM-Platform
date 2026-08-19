from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import OrganizationMode
from app.schemas.common import DepartmentName, OrganizationName


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
