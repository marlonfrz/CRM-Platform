from pydantic import BaseModel, Field, model_validator

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
    owner_password_confirmation: str = Field(min_length=12, max_length=512)

    @model_validator(mode="after")
    def passwords_match(self) -> "SetupRequest":
        if self.owner_password != self.owner_password_confirmation:
            raise ValueError("Passwords do not match")
        return self


class SetupResponse(BaseModel):
    organization_name: str
    owner: AuthenticatedUserResponse
