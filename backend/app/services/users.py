from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole, UserStatus
from app.services.exceptions import LastActiveOwnerError, ResourceNotFoundError


async def disable_user(session: AsyncSession, *, user_id: UUID) -> User:
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise ResourceNotFoundError("User not found")

    if user.role is UserRole.OWNER and user.status is UserStatus.ACTIVE:
        active_owner_count = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.organization_id == user.organization_id,
                User.role == UserRole.OWNER,
                User.status == UserStatus.ACTIVE,
            )
        )
        if active_owner_count is not None and active_owner_count <= 1:
            raise LastActiveOwnerError("The last active owner cannot be disabled")

    user.status = UserStatus.DISABLED
    await session.flush()
    return user
