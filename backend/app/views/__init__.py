from __future__ import annotations

from fastapi import FastAPI

from app.views.sampling_runtime import router as sampling_runtime_router
from app.views.definitions import router as definitions_router
from app.views.health import router as health_router
from app.views.ollama_runtime import router as ollama_runtime_router
from app.views.runtime import router as runtime_router
from app.views.team import router as team_router
from app.views.workflows import router as workflows_router


def register_routers(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(team_router)
    app.include_router(definitions_router)
    app.include_router(workflows_router)
    app.include_router(runtime_router)
    app.include_router(ollama_runtime_router)
    app.include_router(sampling_runtime_router)
