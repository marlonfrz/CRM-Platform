from sqlalchemy import Select, or_, select

from app.models import Activity, Client, ClientAssignment, OrganizationMode, User, UserRole
from app.policies.authorization import AuthorizationContext


def visible_clients(context: AuthorizationContext) -> Select[tuple[Client]]:
    statement = select(Client).where(Client.organization_id == context.organization_id)
    if context.role is UserRole.EMPLOYEE:
        statement = statement.where(
            select(ClientAssignment.id)
            .where(
                ClientAssignment.organization_id == context.organization_id,
                ClientAssignment.client_id == Client.id,
                ClientAssignment.user_id == context.user_id,
            )
            .exists()
        )
    return statement


def visible_activities(context: AuthorizationContext) -> Select[tuple[Activity]]:
    statement = select(Activity).where(Activity.organization_id == context.organization_id)
    if context.organization_mode is OrganizationMode.INDIVIDUAL:
        statement = statement.where(Activity.department_id.is_(None))
    elif not context.is_owner:
        statement = statement.where(Activity.department_id.in_(context.department_ids))
    else:
        statement = statement.where(Activity.department_id.is_not(None))
    if context.role is UserRole.EMPLOYEE:
        statement = statement.where(
            select(ClientAssignment.id)
            .where(
                ClientAssignment.organization_id == context.organization_id,
                ClientAssignment.client_id == Activity.client_id,
                ClientAssignment.user_id == context.user_id,
            )
            .exists()
        )
    return statement


def visible_tasks(context: AuthorizationContext) -> Select[tuple[Activity]]:
    statement = select(Activity).where(Activity.organization_id == context.organization_id)
    if context.organization_mode is OrganizationMode.INDIVIDUAL:
        statement = statement.where(Activity.department_id.is_(None))
    elif not context.is_owner:
        statement = statement.where(Activity.department_id.in_(context.department_ids))
    if context.role is UserRole.ADMIN:
        statement = statement.where(
            or_(
                Activity.assigned_to_user_id == context.user_id,
                select(User.id)
                .where(
                    User.id == Activity.assigned_to_user_id,
                    User.organization_id == context.organization_id,
                    User.role == UserRole.EMPLOYEE,
                )
                .correlate(Activity)
                .exists(),
            )
        )
    if context.role is UserRole.EMPLOYEE:
        statement = statement.where(
            Activity.assigned_to_user_id == context.user_id,
            select(ClientAssignment.id)
            .where(
                ClientAssignment.organization_id == context.organization_id,
                ClientAssignment.client_id == Activity.client_id,
                ClientAssignment.user_id == context.user_id,
            )
            .exists(),
        )
    return statement
