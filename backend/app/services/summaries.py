import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import TypedDict
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context
from app.config import Settings
from app.models import (
    Activity,
    AISummaryCache,
    AISummaryLatest,
    AuditLog,
    Organization,
    OrganizationMode,
)
from app.policies.authorization import AuthorizationContext
from app.schemas.summaries import (
    ProviderSummaryBatch,
    SummaryLatest,
    SummaryRequest,
    SummaryResponse,
    SummarySection,
    SummaryTarget,
    SummaryText,
    SummaryUsage,
)
from app.services.ai_configuration import load_ai_configuration
from app.services.audit import add_audit_event
from app.services.authentication import authenticate_session
from app.services.exceptions import InvalidSessionError
from app.services.scopes import visible_activities
from app.services.summary_context import (
    SummaryGroup,
    authorize_summary_target,
    prepare_summary,
    serialize_audit_context,
    serialize_provider_context,
)
from app.services.summary_cost import estimated_cost_usd
from app.services.summary_provider import (
    SummaryFailure,
    SummaryProvider,
    provider_enabled,
)


class AuditTarget(TypedDict):
    organization_id: UUID
    actor_user_id: UUID
    entity_type: str
    entity_id: UUID


def _latest_scope_key(client_id: UUID | None, department_id: UUID | None) -> str:
    department = str(department_id) if department_id else "personal"
    return (
        f"client:{client_id}:department:{department}" if client_id else f"department:{department}"
    )


async def _store_latest_sections(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    payload: SummaryRequest,
    response: SummaryResponse,
) -> None:
    for section in response.sections:
        values = dict(
            id=uuid4(),
            organization_id=authorization.organization_id,
            scope_key=_latest_scope_key(payload.client_id, section.department_id),
            client_id=payload.client_id,
            department_id=section.department_id,
            provider=response.provider,
            model=response.model,
            generated_at=response.generated_at,
            since=payload.since,
            until=payload.until,
            section=section.model_dump(mode="json"),
        )
        await session.execute(
            insert(AISummaryLatest)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["organization_id", "scope_key"],
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"id", "organization_id", "scope_key"}
                },
                where=AISummaryLatest.generated_at <= response.generated_at,
            )
        )


async def list_latest_summaries(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    target: SummaryTarget,
) -> list[SummaryLatest]:
    await authorize_summary_target(session, authorization, target)
    statement = select(AISummaryLatest).where(
        AISummaryLatest.organization_id == authorization.organization_id,
    )
    if target.client_id:
        statement = statement.where(AISummaryLatest.client_id == target.client_id)
    else:
        statement = statement.where(AISummaryLatest.client_id.is_(None))
    if target.department_id:
        statement = statement.where(AISummaryLatest.department_id == target.department_id)
    elif authorization.organization_mode is OrganizationMode.INDIVIDUAL:
        statement = statement.where(AISummaryLatest.department_id.is_(None))
    else:
        statement = statement.where(AISummaryLatest.department_id.is_not(None))
    if not authorization.is_owner:
        statement = statement.where(AISummaryLatest.department_id.in_(authorization.department_ids))
    rows = list(await session.scalars(statement))
    source_ids = {UUID(source["id"]) for row in rows for source in row.section["sources"]}
    visible_ids: set[UUID] = set()
    if source_ids:
        visible_ids = {
            item.id
            for item in await session.scalars(
                visible_activities(authorization).where(Activity.id.in_(source_ids))
            )
        }
    return sorted(
        [
            SummaryLatest(
                generated_at=row.generated_at,
                since=row.since,
                until=row.until,
                provider=row.provider,
                model=row.model,
                section=SummarySection.model_validate(row.section),
            )
            for row in rows
            if {UUID(source["id"]) for source in row.section["sources"]} <= visible_ids
        ],
        key=lambda item: item.section.department_name or "",
    )


def _sections_from_provider(
    groups: list[SummaryGroup], result: ProviderSummaryBatch
) -> list[SummarySection]:
    items = {item.k: item for item in result.g}
    if len(items) != len(result.g) or set(items) != {group.key for group in groups}:
        raise SummaryFailure("AI_INVALID_OUTPUT", 502)
    sections = []
    for group in groups:
        item = items[group.key]
        source_by_key = {
            str(record[0]): source
            for record, source in zip(group.records, group.sources, strict=True)
        }
        if len(set(item.i)) != len(item.i) or not set(item.i) <= source_by_key.keys():
            raise SummaryFailure("AI_INVALID_OUTPUT", 502)
        sections.append(
            SummarySection(
                department_id=group.department_id,
                department_name=group.department_name,
                content=SummaryText(
                    summary=item.s,
                    pending_actions=item.p,
                    source_ids=[source_by_key[key].id for key in item.i],
                ),
                sources=group.sources,
            )
        )
    return sections


async def _load_cached_response(
    session: AsyncSession,
    *,
    organization_id: UUID,
    provider: str,
    model: str,
    context_sha256: str,
    now: datetime,
) -> SummaryResponse | None:
    cached = await session.scalar(
        select(AISummaryCache).where(
            AISummaryCache.organization_id == organization_id,
            AISummaryCache.provider == provider,
            AISummaryCache.model == model,
            AISummaryCache.context_sha256 == context_sha256,
            AISummaryCache.expires_at > now,
        )
    )
    if cached is None:
        return None
    return SummaryResponse.model_validate(cached.response)


async def _store_cached_response(
    session: AsyncSession,
    *,
    organization_id: UUID,
    provider: str,
    model: str,
    context_sha256: str,
    response: SummaryResponse,
    expires_at: datetime,
) -> None:
    await session.execute(
        insert(AISummaryCache)
        .values(
            id=uuid4(),
            organization_id=organization_id,
            provider=provider,
            model=model,
            context_sha256=context_sha256,
            response=response.model_dump(mode="json"),
            expires_at=expires_at,
        )
        .on_conflict_do_update(
            index_elements=["organization_id", "provider", "model", "context_sha256"],
            set_={
                "response": response.model_dump(mode="json"),
                "expires_at": expires_at,
                "created_at": datetime.now(UTC),
            },
        )
    )


async def generate_summary(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    principal: Principal,
    settings: Settings,
    payload: SummaryRequest,
    provider: SummaryProvider,
) -> SummaryResponse:
    groups = await prepare_summary(session, authorization, payload)
    configuration = await load_ai_configuration(
        session, authorization=authorization, settings=settings
    )
    if not provider_enabled(configuration, settings):
        raise SummaryFailure("AI_NOT_CONFIGURED")
    context_sha256 = sha256(serialize_audit_context(groups).encode()).hexdigest()
    if not groups:
        return SummaryResponse(
            request_id=None,
            generated_at=datetime.now(UTC),
            provider=configuration.provider,
            model=configuration.model,
            sections=[],
        )
    provider_context = serialize_provider_context(groups)
    now = datetime.now(UTC)
    request_id = uuid4()
    audit_args: AuditTarget = dict(
        organization_id=authorization.organization_id,
        actor_user_id=authorization.user_id,
        entity_type="AI_SUMMARY",
        entity_id=request_id,
    )
    cached = (
        await _load_cached_response(
            session,
            organization_id=authorization.organization_id,
            provider=configuration.provider,
            model=configuration.model,
            context_sha256=context_sha256,
            now=now,
        )
        if settings.ai_cache_ttl_seconds
        else None
    )
    if cached is not None:
        response = cached.model_copy(
            update={"request_id": request_id, "cached": True, "usage": None}
        )
        await _store_latest_sections(
            session, authorization=authorization, payload=payload, response=response
        )
        add_audit_event(
            session,
            **audit_args,
            action="AI_SUMMARY_REQUESTED",
            event_data={
                "scope": payload.scope,
                "client_id": str(payload.client_id) if payload.client_id else None,
                "department_id": str(payload.department_id) if payload.department_id else None,
                "provider": configuration.provider,
                "model": configuration.model,
                "source_ids": [str(source.id) for group in groups for source in group.sources],
                "context_sha256": context_sha256,
                "provider_called": False,
            },
        )
        add_audit_event(
            session,
            **audit_args,
            action="AI_SUMMARY_COMPLETED",
            event_data={"cache_hit": True},
        )
        await session.commit()
        return response
    await session.scalar(
        select(Organization.id)
        .where(Organization.id == authorization.organization_id)
        .with_for_update()
    )
    recent = await session.scalar(
        select(AuditLog.id)
        .where(
            AuditLog.organization_id == authorization.organization_id,
            AuditLog.action == "AI_SUMMARY_REQUESTED",
            AuditLog.event_data["provider_called"].as_boolean().is_(True),
            AuditLog.created_at
            >= datetime.now(UTC) - timedelta(seconds=settings.ai_cooldown_seconds),
        )
        .limit(1)
    )
    if recent:
        raise SummaryFailure("AI_RATE_LIMITED", 429)
    add_audit_event(
        session,
        **audit_args,
        action="AI_SUMMARY_REQUESTED",
        event_data={
            "scope": payload.scope,
            "client_id": str(payload.client_id) if payload.client_id else None,
            "department_id": str(payload.department_id) if payload.department_id else None,
            "provider": configuration.provider,
            "model": configuration.model,
            "source_ids": [str(source.id) for group in groups for source in group.sources],
            "context_sha256": context_sha256,
            "provider_called": True,
        },
    )
    await session.commit()
    try:
        async with asyncio.timeout(settings.ai_timeout_seconds):
            provider_result = await provider.summarize(provider_context)
        sections = _sections_from_provider(groups, provider_result.batch)
        await session.refresh(principal.user)
        await session.refresh(principal.session)
        await authenticate_session(session, session_token=principal.session_token)
        fresh = await get_authorization_context(principal, session)
        if fresh != authorization:
            raise SummaryFailure("AI_ACCESS_CHANGED", 403)
    except (SummaryFailure, TimeoutError, InvalidSessionError) as exc:
        code = (
            exc.code
            if isinstance(exc, SummaryFailure)
            else "AI_TIMEOUT"
            if isinstance(exc, TimeoutError)
            else "AI_ACCESS_CHANGED"
        )
        add_audit_event(
            session, **audit_args, action="AI_SUMMARY_FAILED", event_data={"error_code": code}
        )
        await session.commit()
        raise SummaryFailure(
            code,
            exc.status
            if isinstance(exc, SummaryFailure)
            else 504
            if isinstance(exc, TimeoutError)
            else 401,
        ) from None
    response = SummaryResponse(
        request_id=request_id,
        generated_at=datetime.now(UTC),
        provider=configuration.provider,
        model=configuration.model,
        usage=(
            SummaryUsage(
                input_tokens=provider_result.usage.input_tokens,
                output_tokens=provider_result.usage.output_tokens,
                estimated_cost_usd=estimated_cost_usd(
                    configuration.provider,
                    configuration.model,
                    provider_result.usage.input_tokens,
                    provider_result.usage.output_tokens,
                ),
            )
            if provider_result.usage
            else None
        ),
        sections=sections,
    )
    if settings.ai_cache_ttl_seconds:
        await session.execute(
            delete(AISummaryCache).where(
                AISummaryCache.organization_id == authorization.organization_id,
                AISummaryCache.expires_at <= datetime.now(UTC),
            )
        )
        await _store_cached_response(
            session,
            organization_id=authorization.organization_id,
            provider=configuration.provider,
            model=configuration.model,
            context_sha256=context_sha256,
            response=response,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.ai_cache_ttl_seconds),
        )
    await _store_latest_sections(
        session, authorization=authorization, payload=payload, response=response
    )
    add_audit_event(
        session,
        **audit_args,
        action="AI_SUMMARY_COMPLETED",
        event_data={"cache_hit": False},
    )
    await session.commit()
    return response
