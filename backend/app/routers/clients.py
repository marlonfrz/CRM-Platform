from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, get_authorization_context, require_csrf
from app.db.dependencies import get_db_session
from app.policies import AuthorizationContext
from app.schemas.clients import (
    ClientContactRequest,
    ClientContactResponse,
    ClientRequest,
    ClientResponse,
    ClientSummaryResponse,
)
from app.services.clients import (
    create_client,
    create_contact,
    delete_contact,
    get_client,
    list_clients,
    update_client,
    update_contact,
)
from app.services.exceptions import DomainError

from .errors import domain_http_exception

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientSummaryResponse])
async def get_clients(
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> list[ClientSummaryResponse]:
    clients = await list_clients(session, authorization=authorization, search=search)
    return [ClientSummaryResponse.model_validate(client) for client in clients]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def post_client(
    payload: ClientRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientResponse:
    try:
        client = await create_client(
            session,
            authorization=authorization,
            name=payload.name,
            address=payload.address,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return ClientResponse.model_validate(client)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client_detail(
    client_id: UUID,
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientResponse:
    try:
        client = await get_client(session, authorization=authorization, client_id=client_id)
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return ClientResponse.model_validate(client)


@router.patch("/{client_id}", response_model=ClientResponse)
async def patch_client(
    client_id: UUID,
    payload: ClientRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientResponse:
    try:
        client = await update_client(
            session,
            authorization=authorization,
            client_id=client_id,
            name=payload.name,
            address=payload.address,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return ClientResponse.model_validate(client)


@router.post(
    "/{client_id}/contacts",
    response_model=ClientContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_contact(
    client_id: UUID,
    payload: ClientContactRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientContactResponse:
    try:
        contact = await create_contact(
            session,
            authorization=authorization,
            client_id=client_id,
            full_name=payload.full_name,
            position=payload.position,
            email=payload.email,
            phone=payload.phone,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return ClientContactResponse.model_validate(contact)


@router.patch("/{client_id}/contacts/{contact_id}", response_model=ClientContactResponse)
async def patch_contact(
    client_id: UUID,
    contact_id: UUID,
    payload: ClientContactRequest,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientContactResponse:
    try:
        contact = await update_contact(
            session,
            authorization=authorization,
            client_id=client_id,
            contact_id=contact_id,
            full_name=payload.full_name,
            position=payload.position,
            email=payload.email,
            phone=payload.phone,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
    return ClientContactResponse.model_validate(contact)


@router.delete("/{client_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact(
    client_id: UUID,
    contact_id: UUID,
    _: Annotated[Principal, Depends(require_csrf)],
    authorization: Annotated[AuthorizationContext, Depends(get_authorization_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        await delete_contact(
            session,
            authorization=authorization,
            client_id=client_id,
            contact_id=contact_id,
        )
    except DomainError as exc:
        raise domain_http_exception(exc) from exc
