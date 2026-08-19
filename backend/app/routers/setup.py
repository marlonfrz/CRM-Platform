from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.schemas.setup import SetupRequest, SetupResponse, SetupStatusResponse
from app.services.bootstrap import bootstrap_organization
from app.services.exceptions import InstallationAlreadyInitializedError
from app.services.installation import is_installation_initialized

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusResponse)
async def setup_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SetupStatusResponse:
    return SetupStatusResponse(initialized=await is_installation_initialized(session))


@router.post("", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def setup_installation(
    payload: SetupRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SetupResponse:
    try:
        organization, owner = await bootstrap_organization(
            session,
            mode=payload.mode,
            organization_name=payload.organization_name,
            owner_name=payload.owner_name,
            owner_email=payload.owner_email,
            owner_password=payload.owner_password,
        )
    except InstallationAlreadyInitializedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Installation is already initialized",
        ) from exc
    return SetupResponse(
        organization_name=organization.name,
        owner=owner,
    )
