import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, ActivityType, Client, Department, OrganizationMode, UserRole
from app.models.activity import ActivityStatus
from app.policies.authorization import AuthorizationContext
from app.schemas.summaries import SummaryRequest, SummarySource, SummaryTarget
from app.services.clients import get_client
from app.services.exceptions import AuthorizationDeniedError, ResourceNotFoundError
from app.services.scopes import visible_activities
from app.services.summary_provider import SummaryFailure


@dataclass
class SummaryGroup:
    key: str
    department_id: UUID | None
    department_name: str | None
    records: list[list[str | None]]
    sources: list[SummarySource]


def serialize_provider_context(groups: list[SummaryGroup]) -> str:
    return json.dumps(
        {"g": [{"k": group.key, "r": group.records} for group in groups]},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def serialize_audit_context(groups: list[SummaryGroup]) -> str:
    return json.dumps(
        [
            {
                "department_id": str(group.department_id) if group.department_id else None,
                "department_name": group.department_name,
                "records": [
                    [str(source.id), *record[1:]]
                    for source, record in zip(group.sources, group.records, strict=True)
                ],
            }
            for group in groups
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def require_summary_access(authorization: AuthorizationContext) -> None:
    if authorization.role not in {UserRole.OWNER, UserRole.ADMIN}:
        raise AuthorizationDeniedError("Summary access is restricted to managers")


async def authorize_summary_target(
    session: AsyncSession, authorization: AuthorizationContext, target: SummaryTarget
) -> None:
    require_summary_access(authorization)
    if target.scope == "ORGANIZATION" and not authorization.is_owner:
        raise AuthorizationDeniedError("Global summaries require owner access")
    if target.scope == "CLIENT":
        assert target.client_id
        await get_client(session, authorization=authorization, client_id=target.client_id)
    if target.scope == "DEPARTMENT":
        if authorization.organization_mode is OrganizationMode.INDIVIDUAL:
            raise AuthorizationDeniedError("Individual mode has no departments")
        department = await session.get(Department, target.department_id)
        if not department or department.organization_id != authorization.organization_id:
            raise ResourceNotFoundError("Department not found")
        if not authorization.is_owner and department.id not in authorization.department_ids:
            raise AuthorizationDeniedError("Department is outside your scope")


async def prepare_summary(
    session: AsyncSession, authorization: AuthorizationContext, payload: SummaryRequest
) -> list[SummaryGroup]:
    await authorize_summary_target(session, authorization, payload)
    statement = visible_activities(authorization).where(
        or_(
            and_(
                Activity.status == ActivityStatus.COMPLETED.value,
                Activity.occurred_at >= payload.since,
                Activity.occurred_at <= payload.until,
            ),
            and_(
                Activity.status == ActivityStatus.PENDING.value,
                Activity.scheduled_for >= payload.since.date(),
                Activity.scheduled_for <= payload.until.date(),
            ),
        )
    )
    if payload.client_id:
        statement = statement.where(Activity.client_id == payload.client_id)
    if payload.department_id:
        statement = statement.where(Activity.department_id == payload.department_id)
    activities = list(
        await session.execute(
            statement.add_columns(Client.name, Department.name, ActivityType.name)
            .join(Client, Client.id == Activity.client_id)
            .outerjoin(Department, Department.id == Activity.department_id)
            .join(ActivityType, ActivityType.id == Activity.activity_type_id)
            .order_by(Activity.scheduled_for, Activity.id)
            .limit(51)
        )
    )
    if len(activities) > 50:
        raise SummaryFailure("AI_CONTEXT_TOO_LARGE", 413)
    groups: dict[UUID | None, list[tuple[Activity, str, str | None, str]]] = {}
    for activity, client_name, department_name, activity_type_name in activities:
        groups.setdefault(activity.department_id, []).append(
            (activity, client_name, department_name, activity_type_name)
        )
    if len(groups) > 8:
        raise SummaryFailure("AI_CONTEXT_TOO_LARGE", 413)
    result: list[SummaryGroup] = []
    source_number = 0
    for department_id, entries in groups.items():
        sources = []
        records = []
        for activity, client_name, _, activity_type_name in entries:
            sources.append(
                SummarySource(
                    id=activity.id,
                    client_id=activity.client_id,
                    client_name=client_name,
                    activity_type_name=activity_type_name,
                    title=activity.title,
                    description=activity.description,
                    status=activity.status,
                    scheduled_for=activity.scheduled_for,
                    occurred_at=activity.occurred_at,
                )
            )
            records.append(
                [
                    f"r{source_number}",
                    client_name,
                    activity_type_name,
                    activity.title,
                    activity.status,
                    (
                        activity.occurred_at.strftime("%Y-%m-%dT%H:%MZ")
                        if activity.occurred_at
                        else activity.scheduled_for.isoformat()
                    ),
                    activity.description,
                    activity.next_action,
                ]
            )
            source_number += 1
        result.append(
            SummaryGroup(f"g{len(result)}", department_id, entries[0][2], records, sources)
        )
    if len(serialize_provider_context(result).encode()) > 32000:
        raise SummaryFailure("AI_CONTEXT_TOO_LARGE", 413)
    return result
