from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.services.normalization import normalize_email

ClientName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Address = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
OptionalNote = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
Position = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]


class ClientRequest(BaseModel):
    name: ClientName
    address: Address | None = None
    notes: OptionalNote | None = None


class ClientContactRequest(BaseModel):
    full_name: ClientName
    position: Position | None = None
    email: str | None = None
    phone: Phone | None = None
    notes: OptionalNote | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return normalize_email(value)


class ClientContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    position: str | None
    email: str | None
    phone: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ClientSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str | None
    created_at: datetime
    updated_at: datetime


class ClientResponse(ClientSummaryResponse):
    notes: str | None
    contacts: list[ClientContactResponse]
