import os

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models import (
    DepartmentMember,
    Organization,
    OrganizationMode,
    User,
    UserRole,
    UserStatus,
)
from app.services.bootstrap import bootstrap_organization
from app.services.departments import add_department_member, create_department
from app.services.exceptions import (
    IndividualModeViolationError,
    InstallationAlreadyInitializedError,
    LastActiveOwnerError,
)
from app.services.users import disable_user

PASSWORD = "a-secure-bootstrap-password"
TEST_DATABASE_URL = os.environ["DATABASE_URL"]


async def bootstrap(
    session: AsyncSession, mode: OrganizationMode = OrganizationMode.BUSINESS
) -> tuple[Organization, User]:
    return await bootstrap_organization(
        session,
        mode=mode,
        organization_name="Example Organization",
        owner_name="Primary Owner",
        owner_email="  OWNER@Example.com ",
        owner_password=PASSWORD,
    )


async def test_initial_migration_creates_foundation_tables() -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
    await engine.dispose()

    assert {"organizations", "users", "departments", "department_members"} <= set(table_names)


async def test_business_bootstrap_creates_normalized_active_owner(
    db_session: AsyncSession,
) -> None:
    organization, owner = await bootstrap(db_session)

    assert organization.mode is OrganizationMode.BUSINESS
    assert owner.organization_id == organization.id
    assert owner.email == "owner@example.com"
    assert owner.role is UserRole.OWNER
    assert owner.status is UserStatus.ACTIVE
    assert owner.password_hash is not None
    assert owner.password_hash != PASSWORD


async def test_installation_can_only_be_bootstrapped_once(db_session: AsyncSession) -> None:
    await bootstrap(db_session)

    try:
        await bootstrap(db_session)
    except InstallationAlreadyInitializedError:
        pass
    else:
        raise AssertionError("A second bootstrap must be rejected")


async def test_individual_mode_rejects_departments(db_session: AsyncSession) -> None:
    organization, _ = await bootstrap(db_session, OrganizationMode.INDIVIDUAL)

    try:
        await create_department(db_session, organization_id=organization.id, name="Sales")
    except IndividualModeViolationError:
        pass
    else:
        raise AssertionError("Individual organizations cannot create departments")


async def test_business_user_can_belong_to_multiple_departments(
    db_session: AsyncSession,
) -> None:
    organization, owner = await bootstrap(db_session)
    sales = await create_department(db_session, organization_id=organization.id, name="Sales")
    marketing = await create_department(
        db_session, organization_id=organization.id, name="Marketing"
    )

    first = await add_department_member(
        db_session,
        organization_id=organization.id,
        department_id=sales.id,
        user_id=owner.id,
    )
    second = await add_department_member(
        db_session,
        organization_id=organization.id,
        department_id=marketing.id,
        user_id=owner.id,
    )

    assert first.user_id == second.user_id == owner.id
    assert first.department_id != second.department_id


async def test_cross_organization_membership_is_rejected(db_session: AsyncSession) -> None:
    first_organization, first_owner = await bootstrap(db_session)
    first_department = await create_department(
        db_session, organization_id=first_organization.id, name="Sales"
    )
    second_organization = Organization(name="Second Organization", mode=OrganizationMode.BUSINESS)
    second_user = User(
        organization=second_organization,
        email="second@example.com",
        full_name="Second User",
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        password_hash="already-hashed",
    )
    db_session.add_all([second_organization, second_user])
    await db_session.flush()

    membership = DepartmentMember(
        organization_id=first_organization.id,
        department_id=first_department.id,
        user_id=second_user.id,
    )
    db_session.add(membership)

    try:
        await db_session.flush()
    except IntegrityError:
        await db_session.rollback()
    else:
        raise AssertionError("Cross-organization membership must violate its foreign key")

    assert first_owner.organization_id != second_user.organization_id


async def test_duplicate_normalized_email_is_rejected(db_session: AsyncSession) -> None:
    organization, _ = await bootstrap(db_session)
    duplicate = User(
        organization_id=organization.id,
        email="owner@example.com",
        full_name="Duplicate",
        role=UserRole.EMPLOYEE,
        status=UserStatus.PENDING,
    )
    db_session.add(duplicate)

    try:
        await db_session.flush()
    except IntegrityError:
        await db_session.rollback()
    else:
        raise AssertionError("Email must be unique inside an organization")


async def test_last_active_owner_cannot_be_disabled(db_session: AsyncSession) -> None:
    _, owner = await bootstrap(db_session)

    try:
        await disable_user(db_session, user_id=owner.id)
    except LastActiveOwnerError:
        pass
    else:
        raise AssertionError("The final active owner must be protected")
