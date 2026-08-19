class DomainError(Exception):
    pass


class InstallationAlreadyInitializedError(DomainError):
    pass


class IndividualModeViolationError(DomainError):
    pass


class LastActiveOwnerError(DomainError):
    pass


class ResourceNotFoundError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class InvalidSessionError(DomainError):
    pass
