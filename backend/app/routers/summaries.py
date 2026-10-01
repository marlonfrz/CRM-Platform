from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.config import Settings, get_settings
from app.db.dependencies import get_db_session
from app.policies.authorization import AuthorizationContext
from app.schemas.summaries import (
    AIConfigurationResponse,
    SummaryDepartment,
    SummaryLatest,
    SummaryOptions,
    SummaryRequest,
    SummaryResponse,
    SummaryTarget,
    UpdateAIConfigurationRequest,
)
from app.services.ai_configuration import (
    configuration_response,
    load_ai_configuration,
    require_ai_configuration_access,
    update_ai_configuration,
)
from app.services.departments import list_departments
from app.services.exceptions import DomainError, InvalidAIConfigurationError
from app.services.summaries import generate_summary, list_latest_summaries
from app.services.summary_context import require_summary_access
from app.services.summary_provider import (
    HttpSummaryProvider,
    SummaryFailure,
    SummaryProvider,
    provider_enabled,
)

from .errors import domain_http_exception

router = APIRouter(prefix="/ai", tags=["summaries"])
Authorization = Annotated[AuthorizationContext, Depends(get_authorization_context)]
Database = Annotated[AsyncSession, Depends(get_db_session)]
Configuration = Annotated[Settings, Depends(get_settings)]


async def get_summary_provider(
    settings: Configuration, authorization: Authorization, session: Database
) -> SummaryProvider:
    configuration = await load_ai_configuration(
        session, authorization=authorization, settings=settings
    )
    return HttpSummaryProvider(settings, configuration)


@router.get("/options", response_model=SummaryOptions)
async def get_options(
    authorization: Authorization, session: Database, settings: Configuration
) -> SummaryOptions:
    try:
        require_summary_access(authorization)
        configuration = await load_ai_configuration(
            session, authorization=authorization, settings=settings
        )
        departments = await list_departments(session, authorization=authorization)
        return SummaryOptions(
            enabled=provider_enabled(configuration, settings),
            provider=configuration.provider,
            model=configuration.model,
            external=configuration.external,
            departments=[SummaryDepartment(id=item.id, name=item.name) for item in departments],
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.get("/configuration", response_model=AIConfigurationResponse)
async def get_configuration(
    authorization: Authorization, session: Database, settings: Configuration
) -> AIConfigurationResponse:
    try:
        require_ai_configuration_access(authorization)
        configuration = await load_ai_configuration(
            session, authorization=authorization, settings=settings
        )
        return configuration_response(configuration)
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.put("/configuration", response_model=AIConfigurationResponse)
async def put_configuration(
    payload: UpdateAIConfigurationRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Authorization,
    session: Database,
    settings: Configuration,
) -> AIConfigurationResponse:
    try:
        configuration = await update_ai_configuration(
            session,
            authorization=authorization,
            settings=settings,
            payload=payload,
        )
        return configuration_response(configuration)
    except InvalidAIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="AI_API_KEY_REQUIRED",
        ) from exc
    except DomainError as exc:
        raise domain_http_exception(exc) from exc


@router.post("/summaries", response_model=SummaryResponse)
async def post_summary(
    payload: SummaryRequest,
    principal: Annotated[Principal, Depends(require_csrf)],
    authorization: Authorization,
    session: Database,
    settings: Configuration,
    provider: Annotated[SummaryProvider, Depends(get_summary_provider)],
) -> SummaryResponse:
    try:
        return await generate_summary(
            session,
            authorization=authorization,
            principal=principal,
            settings=settings,
            payload=payload,
            provider=provider,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    except SummaryFailure as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc


@router.get("/summaries/latest", response_model=list[SummaryLatest])
async def get_latest_summaries(
    target: Annotated[SummaryTarget, Query()],
    authorization: Authorization,
    session: Database,
) -> list[SummaryLatest]:
    try:
        return await list_latest_summaries(session, authorization=authorization, target=target)
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
