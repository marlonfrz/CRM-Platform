from enum import StrEnum


class OrganizationMode(StrEnum):
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"


class UserRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"


class UserStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
