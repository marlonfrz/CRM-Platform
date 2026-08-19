import argparse
import asyncio
from getpass import getpass

from app.db.session import engine, session_factory
from app.models import OrganizationMode
from app.services.bootstrap import bootstrap_organization


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a CRM Platform installation")
    parser.add_argument("--mode", choices=[mode.value for mode in OrganizationMode], required=True)
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--owner-name", required=True)
    parser.add_argument("--owner-email", required=True)
    return parser.parse_args()


async def run_bootstrap(arguments: argparse.Namespace) -> None:
    password = getpass("Owner password: ")
    confirmation = getpass("Confirm owner password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match")

    async with session_factory() as session, session.begin():
        organization, owner = await bootstrap_organization(
            session,
            mode=OrganizationMode(arguments.mode),
            organization_name=arguments.organization_name,
            owner_name=arguments.owner_name,
            owner_email=arguments.owner_email,
            owner_password=password,
        )
    print(f"Created {organization.mode.value} organization '{organization.name}'")
    print(f"Created active owner '{owner.email}'")


def main() -> None:
    try:
        asyncio.run(run_bootstrap(parse_arguments()))
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()
