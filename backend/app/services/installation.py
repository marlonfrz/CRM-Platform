from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization


async def lock_installation_setup(session: AsyncSession) -> None:
    await session.scalar(select(func.pg_advisory_xact_lock(742918305)))


async def is_installation_initialized(session: AsyncSession) -> bool:
    organization_count = await session.scalar(select(func.count()).select_from(Organization))
    return bool(organization_count)
