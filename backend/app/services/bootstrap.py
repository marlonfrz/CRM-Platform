from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityType, Organization, OrganizationMode, User, UserRole, UserStatus
from app.models.activity_type import activity_type_identifier
from app.services.audit import add_audit_event
from app.services.exceptions import InstallationAlreadyInitializedError
from app.services.installation import is_installation_initialized, lock_installation_setup
from app.services.normalization import normalize_email, normalize_name

password_hasher = PasswordHasher()
DEFAULT_ACTIVITY_TYPES = (
    ("Llamada", "llamada"),
    ("Email", "email"),
    ("Reunión", "reunión"),
    ("Nota", "nota"),
    ("Incidencia", "incidencia"),
    ("Otro", "otro"),
)


async def bootstrap_organization(
    session: AsyncSession,
    *,
    mode: OrganizationMode,
    organization_name: str,
    owner_name: str,
    owner_email: str,
    owner_password: str,
) -> tuple[Organization, User]:
    await lock_installation_setup(session)
    if await is_installation_initialized(session):
        raise InstallationAlreadyInitializedError("The installation is already initialized")
    if len(owner_password) < 12:
        raise ValueError("The owner password must contain at least 12 characters")

    organization = Organization(name=normalize_name(organization_name), mode=mode)
    owner = User(
        organization=organization,
        email=normalize_email(owner_email),
        full_name=normalize_name(owner_name),
        password_hash=password_hasher.hash(owner_password),
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    session.add_all([organization, owner])
    await session.flush()
    session.add_all(
        [
            ActivityType(
                id=activity_type_identifier(organization.id, normalized),
                organization_id=organization.id,
                department_id=None,
                name=name,
                normalized_name=normalized,
                is_active=True,
            )
            for name, normalized in DEFAULT_ACTIVITY_TYPES
        ]
    )
    await session.flush()
    add_audit_event(
        session,
        organization_id=organization.id,
        actor_user_id=owner.id,
        action="INITIALIZED_ORGANIZATION",
        entity_type="ORGANIZATION",
        entity_id=organization.id,
    )
    return organization, owner
