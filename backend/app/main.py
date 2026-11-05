"""FastAPI composition root. Run from the repository root with Poetry."""
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.agents.factory import AgnoRunner
from backend.app.agents.registry import AgentRegistry
from backend.app.api import agents, analytics, health, history, runs
from backend.app.core.config import Settings
from backend.app.core.errors import ApplicationError
from backend.app.orchestration.coordinator import Coordinator
from backend.app.services.models import ModelService
from backend.app.services.analytics import AnalyticsService
from backend.app.storage.agents import AgentRepository
from backend.app.storage.database import Database
from backend.app.storage.runs import RunRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient() as client:
            database = Database(settings.database_path)
            app.state.history = RunRepository(database)
            app.state.history.recover_interrupted()
            app.state.analytics = AnalyticsService(database)
            app.state.registry = AgentRegistry(AgentRepository(database))
            app.state.models = ModelService(settings, client)
            app.state.coordinator = Coordinator(AgnoRunner(settings))
            yield

    app = FastAPI(title="DecisionMesh API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"])

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(health.router)
    app.include_router(agents.router)
    app.include_router(runs.router)
    app.include_router(history.router)
    app.include_router(analytics.router)
    return app


app = create_app()
