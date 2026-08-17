from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import get_settings


def create_database_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


engine = create_database_engine()
