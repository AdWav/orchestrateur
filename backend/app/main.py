from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import ui_allowed_origins
from app.dependencies import init_container, reset_container
from app.views import register_routers


def create_app() -> FastAPI:
    reset_container()
    init_container()

    application = FastAPI(
        title="Orchestrateur Local Multi-Agents",
        version="0.2.0",
        description="Control plane Python-first pour agents locaux specialises (MVC).",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=ui_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routers(application)
    return application


app = create_app()
