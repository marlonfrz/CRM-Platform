from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization
from app.policies.authorization import AuthorizationContext, can_manage_organization
from app.services.audit import add_audit_event
from app.services.exceptions import AuthorizationDeniedError, ResourceNotFoundError
from app.services.normalization import normalize_name


async def update_organization(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    name: str,
) -> Organization:
    organization = await session.get(Organization, authorization.organization_id)
    if organization is None:
        raise ResourceNotFoundError("Organization not found")
    if not can_manage_organization(authorization, organization.id):
        raise AuthorizationDeniedError("Organization management is not allowed")

    previous_name = organization.name
    organization.name = normalize_name(name)
    add_audit_event(
        session,
        organization_id=organization.id,
        actor_user_id=authorization.user_id,
        action="UPDATED_ORGANIZATION",
        entity_type="ORGANIZATION",
        entity_id=organization.id,
        event_data={"previous_name": previous_name, "name": organization.name},
    )
    await session.flush()
    return organization
