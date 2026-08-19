from dataclasses import dataclass
from uuid import UUID

from app.models import OrganizationMode, UserRole


@dataclass(frozen=True)
class AuthorizationContext:
    user_id: UUID
    organization_id: UUID
    organization_mode: OrganizationMode
    role: UserRole
    department_ids: frozenset[UUID] = frozenset()

    @property
    def is_owner(self) -> bool:
        return self.role is UserRole.OWNER

    def belongs_to_organization(self, organization_id: UUID) -> bool:
        return self.organization_id == organization_id

    def has_department(self, department_id: UUID | None) -> bool:
        return department_id is not None and department_id in self.department_ids


def can_manage_organization(context: AuthorizationContext, organization_id: UUID) -> bool:
    return context.belongs_to_organization(organization_id) and context.is_owner


def can_manage_department(
    context: AuthorizationContext, *, organization_id: UUID, department_id: UUID
) -> bool:
    if not context.belongs_to_organization(organization_id):
        return False
    return context.is_owner or (
        context.role is UserRole.ADMIN and context.has_department(department_id)
    )


def can_manage_user(
    context: AuthorizationContext,
    *,
    organization_id: UUID,
    target_role: UserRole,
    target_department_ids: frozenset[UUID],
) -> bool:
    if not context.belongs_to_organization(organization_id):
        return False
    if context.is_owner:
        return True
    return (
        context.role is UserRole.ADMIN
        and target_role is UserRole.EMPLOYEE
        and bool(target_department_ids)
        and target_department_ids.issubset(context.department_ids)
    )


def can_view_client(
    context: AuthorizationContext, *, organization_id: UUID, is_assigned: bool
) -> bool:
    if not context.belongs_to_organization(organization_id):
        return False
    return context.role in {UserRole.OWNER, UserRole.ADMIN} or is_assigned


def can_manage_client(context: AuthorizationContext, *, organization_id: UUID) -> bool:
    return context.belongs_to_organization(organization_id) and context.role in {
        UserRole.OWNER,
        UserRole.ADMIN,
    }


def can_assign_client(
    context: AuthorizationContext,
    *,
    organization_id: UUID,
    target_role: UserRole,
    target_department_ids: frozenset[UUID],
) -> bool:
    if not context.belongs_to_organization(organization_id):
        return False
    if context.is_owner:
        return True
    return (
        context.role is UserRole.ADMIN
        and target_role is UserRole.EMPLOYEE
        and bool(context.department_ids & target_department_ids)
    )


def can_create_activity(
    context: AuthorizationContext,
    *,
    organization_id: UUID,
    department_id: UUID | None,
    is_client_assigned: bool,
) -> bool:
    if not context.belongs_to_organization(organization_id):
        return False
    if context.organization_mode is OrganizationMode.INDIVIDUAL:
        return context.is_owner and department_id is None
    if department_id is None:
        return False
    if context.is_owner:
        return True
    if not context.has_department(department_id):
        return False
    return context.role in {UserRole.OWNER, UserRole.ADMIN} or is_client_assigned


def can_view_activity(
    context: AuthorizationContext,
    *,
    organization_id: UUID,
    department_id: UUID | None,
    is_client_assigned: bool,
) -> bool:
    if not context.belongs_to_organization(organization_id):
        return False
    if context.is_owner:
        if context.organization_mode is OrganizationMode.INDIVIDUAL:
            return department_id is None
        return department_id is not None
    if not context.has_department(department_id):
        return False
    return context.role is UserRole.ADMIN or is_client_assigned


def can_manage_task(
    context: AuthorizationContext,
    *,
    organization_id: UUID,
    department_id: UUID | None,
    is_assigned_to_actor: bool,
    is_client_assigned: bool,
) -> bool:
    if not context.belongs_to_organization(organization_id):
        return False
    if context.is_owner:
        return True
    if not context.has_department(department_id):
        return False
    if context.role is UserRole.ADMIN:
        return True
    return is_assigned_to_actor and is_client_assigned


def can_view_global_report(context: AuthorizationContext, organization_id: UUID) -> bool:
    return context.belongs_to_organization(organization_id) and context.is_owner


def can_view_department_report(
    context: AuthorizationContext, *, organization_id: UUID, department_id: UUID
) -> bool:
    return can_manage_department(
        context, organization_id=organization_id, department_id=department_id
    )
