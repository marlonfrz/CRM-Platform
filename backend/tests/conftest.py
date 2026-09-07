import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://crm_platform:development-only@localhost:5432/crm_platform_test",
)
if not TEST_DATABASE_URL.rsplit("/", maxsplit=1)[-1].endswith("_test"):
    raise RuntimeError("Integration tests require a database whose name ends with '_test'")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db.dependencies import get_db_session  # noqa: E402
from app.main import app  # noqa: E402

test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_db_session() -> AsyncIterator[AsyncSession]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db_session] = override_db_session


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with test_session_factory() as session:
        yield session
        await session.rollback()
    async with test_engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE tasks, activities, audit_logs, client_assignments, "
                "client_contacts, clients, user_invitations, user_sessions, "
                "department_members, departments, users, "
                "organizations CASCADE"
            )
        )


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as client:
        yield client
