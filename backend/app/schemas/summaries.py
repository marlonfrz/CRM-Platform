from datetime import date, datetime, timedelta
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    model_validator,
)

Scope = Literal["CLIENT", "DEPARTMENT", "ORGANIZATION"]
AIProviderName = Literal["disabled", "ollama", "openai", "anthropic", "gemini"]
Text = Annotated[str, StringConstraints(min_length=1, max_length=2000)]
PendingText = Annotated[str, StringConstraints(min_length=1, max_length=400)]
CompactText = Annotated[str, StringConstraints(min_length=1, max_length=600)]
CompactPendingText = Annotated[str, StringConstraints(min_length=1, max_length=180)]
GroupKey = Annotated[str, StringConstraints(pattern=r"^g[0-7]$")]
SourceKey = Annotated[str, StringConstraints(pattern=r"^r(?:[0-9]|[1-4][0-9])$")]
ModelName = Annotated[str, StringConstraints(max_length=100, pattern=r"^[a-zA-Z0-9._:/-]*$")]


class SummaryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Scope
    client_id: UUID | None = None
    department_id: UUID | None = None

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        if (self.scope == "CLIENT") != (self.client_id is not None):
            raise ValueError("Client scope requires only a client ID")
        if (self.scope == "DEPARTMENT") != (self.department_id is not None):
            raise ValueError("Department scope requires only a department ID")
        return self


class SummaryRequest(SummaryTarget):
    since: AwareDatetime
    until: AwareDatetime

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.since > self.until or self.until - self.since > timedelta(days=366):
            raise ValueError("Select a date range of at most 366 days")
        return self


class SummaryText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: Text
    pending_actions: Annotated[list[PendingText], Field(max_length=8)]
    source_ids: Annotated[list[UUID], Field(min_length=1, max_length=50)]


class ProviderSummarySection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    k: GroupKey
    s: CompactText
    p: Annotated[list[CompactPendingText], Field(max_length=4)]
    i: Annotated[list[SourceKey], Field(min_length=1, max_length=50)]


class ProviderSummaryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    g: Annotated[list[ProviderSummarySection], Field(min_length=1, max_length=8)]


class SummarySource(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    activity_type_name: str
    title: str | None
    description: str
    status: Literal["PENDING", "COMPLETED"]
    scheduled_for: date
    occurred_at: datetime | None


class SummarySection(BaseModel):
    department_id: UUID | None
    department_name: str | None
    content: SummaryText
    sources: list[SummarySource]


class SummaryUsage(BaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float | None = None


class SummaryResponse(BaseModel):
    request_id: UUID | None
    generated_at: datetime
    provider: str
    model: str
    cached: bool = False
    usage: SummaryUsage | None = None
    sections: list[SummarySection]


class SummaryLatest(BaseModel):
    generated_at: datetime
    since: datetime
    until: datetime
    provider: str
    model: str
    section: SummarySection


class SummaryDepartment(BaseModel):
    id: UUID
    name: str


class SummaryOptions(BaseModel):
    enabled: bool
    provider: AIProviderName
    model: str
    external: bool
    departments: list[SummaryDepartment]


class AIConfigurationResponse(BaseModel):
    provider: AIProviderName
    model: str
    has_api_key: bool
    source: Literal["organization", "environment"]


class UpdateAIConfigurationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: AIProviderName
    model: ModelName = ""
    api_key: SecretStr | None = Field(default=None, min_length=8, max_length=2048)

    @model_validator(mode="after")
    def require_model_for_enabled_provider(self) -> "UpdateAIConfigurationRequest":
        if self.provider != "disabled" and not self.model:
            raise ValueError("Enabled AI providers require a model")
        return self
