from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import UserStatus


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class AssignmentUserResponse(BaseModel):
    user_id: UUID
    full_name: str
    status: UserStatus


class AssignmentTeamResponse(BaseModel):
    assigned: list[AssignmentUserResponse]
    available: list[AssignmentUserResponse]
