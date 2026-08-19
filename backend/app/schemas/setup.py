from pydantic import BaseModel, Field

from app.models import OrganizationMode
from app.schemas.auth import AuthenticatedUserResponse


class SetupStatusResponse(BaseModel):
    initialized: bool


class SetupRequest(BaseModel):
    mode: OrganizationMode
    organization_name: str = Field(min_length=1, max_length=200)
    owner_name: str = Field(min_length=1, max_length=200)
    owner_email: str = Field(min_length=3, max_length=320)
    owner_password: str = Field(min_length=12, max_length=512)


class SetupResponse(BaseModel):
    organization_name: str
    owner: AuthenticatedUserResponse
