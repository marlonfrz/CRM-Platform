from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, OrganizationMode, User, UserRole, UserStatus
from app.services.exceptions import InstallationAlreadyInitializedError
from app.services.installation import is_installation_initialized, lock_installation_setup
from app.services.normalization import normalize_email, normalize_name

password_hasher = PasswordHasher()


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
    return organization, owner
