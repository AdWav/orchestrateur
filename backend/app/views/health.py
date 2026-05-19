from __future__ import annotations

from fastapi import APIRouter

from app.controllers import health_controller
from app.models.api_schemas import HealthResponse, ServiceMeshStatusResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return health_controller.health()


@router.get("/services/status", response_model=ServiceMeshStatusResponse)
def service_status() -> ServiceMeshStatusResponse:
    return health_controller.service_status()
