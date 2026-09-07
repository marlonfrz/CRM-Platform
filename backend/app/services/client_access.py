from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client
from app.policies.authorization import AuthorizationContext
from app.services.clients import get_client
from app.services.exceptions import ResourceNotFoundError


async def lock_accessible_client(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
) -> None:
    client = await session.scalar(
        select(Client)
        .where(
            Client.id == client_id,
            Client.organization_id == authorization.organization_id,
        )
        .with_for_update()
    )
    if client is None:
        raise ResourceNotFoundError("Client not found")
    await get_client(session, authorization=authorization, client_id=client_id)
