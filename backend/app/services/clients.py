from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Client, ClientAssignment, ClientContact
from app.policies.authorization import AuthorizationContext, can_manage_client, can_view_client
from app.services.audit import add_audit_event
from app.services.exceptions import AuthorizationDeniedError, ResourceNotFoundError
from app.services.normalization import normalize_email, normalize_name, normalize_optional_text
from app.services.scopes import visible_clients


async def list_clients(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    search: str | None = None,
) -> list[Client]:
    statement = visible_clients(authorization)
    normalized_search = normalize_optional_text(search)
    if normalized_search:
        statement = statement.where(Client.name.icontains(normalized_search, autoescape=True))
    return list(await session.scalars(statement.order_by(Client.name, Client.id)))


async def get_client(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
) -> Client:
    client = await _get_organization_client(session, authorization.organization_id, client_id)
    is_assigned = (
        await session.scalar(
            select(ClientAssignment.id).where(
                ClientAssignment.organization_id == authorization.organization_id,
                ClientAssignment.client_id == client_id,
                ClientAssignment.user_id == authorization.user_id,
            )
        )
        is not None
    )
    if not can_view_client(
        authorization, organization_id=client.organization_id, is_assigned=is_assigned
    ):
        raise AuthorizationDeniedError("Client access is not allowed")
    return client


async def create_client(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    name: str,
    address: str | None,
    notes: str | None,
) -> Client:
    _require_client_management(authorization)
    client = Client(
        organization_id=authorization.organization_id,
        name=normalize_name(name),
        address=normalize_optional_text(address),
        notes=normalize_optional_text(notes),
        contacts=[],
    )
    session.add(client)
    await session.flush()
    add_audit_event(
        session,
        organization_id=client.organization_id,
        actor_user_id=authorization.user_id,
        action="CREATED_CLIENT",
        entity_type="CLIENT",
        entity_id=client.id,
        event_data={"name": client.name},
    )
    return client


async def update_client(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    name: str,
    address: str | None,
    notes: str | None,
) -> Client:
    client = await _get_managed_client(session, authorization, client_id, for_update=True)
    previous_name = client.name
    client.name = normalize_name(name)
    client.address = normalize_optional_text(address)
    client.notes = normalize_optional_text(notes)
    add_audit_event(
        session,
        organization_id=client.organization_id,
        actor_user_id=authorization.user_id,
        action="UPDATED_CLIENT",
        entity_type="CLIENT",
        entity_id=client.id,
        event_data={"previous_name": previous_name, "name": client.name},
    )
    await session.flush()
    await session.refresh(client, attribute_names=["updated_at"])
    return client


async def create_contact(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    full_name: str,
    position: str | None,
    email: str | None,
    phone: str | None,
    notes: str | None,
) -> ClientContact:
    client = await _get_managed_client(session, authorization, client_id)
    contact = ClientContact(
        organization_id=client.organization_id,
        client_id=client.id,
        full_name=normalize_name(full_name),
        position=normalize_optional_text(position),
        email=_normalize_optional_email(email),
        phone=normalize_optional_text(phone),
        notes=normalize_optional_text(notes),
    )
    session.add(contact)
    await session.flush()
    add_audit_event(
        session,
        organization_id=client.organization_id,
        actor_user_id=authorization.user_id,
        action="CREATED_CLIENT_CONTACT",
        entity_type="CLIENT_CONTACT",
        entity_id=contact.id,
        event_data={"client_id": str(client.id), "full_name": contact.full_name},
    )
    return contact


async def update_contact(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    contact_id: UUID,
    full_name: str,
    position: str | None,
    email: str | None,
    phone: str | None,
    notes: str | None,
) -> ClientContact:
    client = await _get_managed_client(session, authorization, client_id)
    contact = await _get_contact(session, client, contact_id, for_update=True)
    previous_name = contact.full_name
    contact.full_name = normalize_name(full_name)
    contact.position = normalize_optional_text(position)
    contact.email = _normalize_optional_email(email)
    contact.phone = normalize_optional_text(phone)
    contact.notes = normalize_optional_text(notes)
    add_audit_event(
        session,
        organization_id=client.organization_id,
        actor_user_id=authorization.user_id,
        action="UPDATED_CLIENT_CONTACT",
        entity_type="CLIENT_CONTACT",
        entity_id=contact.id,
        event_data={
            "client_id": str(client.id),
            "previous_name": previous_name,
            "full_name": contact.full_name,
        },
    )
    await session.flush()
    await session.refresh(contact, attribute_names=["updated_at"])
    return contact


async def delete_contact(
    session: AsyncSession,
    *,
    authorization: AuthorizationContext,
    client_id: UUID,
    contact_id: UUID,
) -> None:
    client = await _get_managed_client(session, authorization, client_id)
    contact = await _get_contact(session, client, contact_id, for_update=True)
    add_audit_event(
        session,
        organization_id=client.organization_id,
        actor_user_id=authorization.user_id,
        action="DELETED_CLIENT_CONTACT",
        entity_type="CLIENT_CONTACT",
        entity_id=contact.id,
        event_data={"client_id": str(client.id), "full_name": contact.full_name},
    )
    await session.delete(contact)


async def _get_organization_client(
    session: AsyncSession,
    organization_id: UUID,
    client_id: UUID,
    *,
    for_update: bool = False,
) -> Client:
    statement = (
        select(Client)
        .options(selectinload(Client.contacts))
        .where(Client.id == client_id, Client.organization_id == organization_id)
    )
    if for_update:
        statement = statement.with_for_update()
    client = await session.scalar(statement)
    if client is None:
        raise ResourceNotFoundError("Client not found")
    return client


async def _get_managed_client(
    session: AsyncSession,
    authorization: AuthorizationContext,
    client_id: UUID,
    *,
    for_update: bool = False,
) -> Client:
    client = await _get_organization_client(
        session, authorization.organization_id, client_id, for_update=for_update
    )
    if not can_manage_client(authorization, organization_id=client.organization_id):
        raise AuthorizationDeniedError("Client management is not allowed")
    return client


async def _get_contact(
    session: AsyncSession,
    client: Client,
    contact_id: UUID,
    *,
    for_update: bool,
) -> ClientContact:
    statement = select(ClientContact).where(
        ClientContact.id == contact_id,
        ClientContact.organization_id == client.organization_id,
        ClientContact.client_id == client.id,
    )
    if for_update:
        statement = statement.with_for_update()
    contact = await session.scalar(statement)
    if contact is None:
        raise ResourceNotFoundError("Client contact not found")
    return contact


def _require_client_management(authorization: AuthorizationContext) -> None:
    if not can_manage_client(authorization, organization_id=authorization.organization_id):
        raise AuthorizationDeniedError("Client management is not allowed")


def _normalize_optional_email(value: str | None) -> str | None:
    normalized = normalize_optional_text(value)
    return normalize_email(normalized) if normalized else None
