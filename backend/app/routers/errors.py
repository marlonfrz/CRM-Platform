from fastapi import HTTPException, status

from app.services.exceptions import (
    AuthorizationDeniedError,
    IndividualModeViolationError,
    LastActiveOwnerError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def domain_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, AuthorizationDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if isinstance(error, ResourceNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    if isinstance(error, IndividualModeViolationError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operation is not available in individual mode",
        )
    if isinstance(error, ResourceConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource conflict")
    if isinstance(error, LastActiveOwnerError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Last active owner")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid operation")
