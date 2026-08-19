from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine
from app.routers.health import router as health_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="CRM Platform API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router, prefix="/api/v1")
