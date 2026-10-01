from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine
from app.routers.activities import router as activities_router
from app.routers.activity_types import router as activity_types_router
from app.routers.administration import router as administration_router
from app.routers.assignments import router as assignments_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.health import router as health_router
from app.routers.insights import router as insights_router
from app.routers.setup import router as setup_router
from app.routers.summaries import router as summaries_router
from app.routers.tasks import router as tasks_router
from app.routers.workspace import router as workspace_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="CRM Platform API", version="0.1.0", lifespan=lifespan)
app.include_router(activities_router, prefix="/api/v1")
app.include_router(activity_types_router, prefix="/api/v1")
app.include_router(administration_router, prefix="/api/v1")
app.include_router(assignments_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(clients_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(setup_router, prefix="/api/v1")
app.include_router(summaries_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
