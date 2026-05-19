from __future__ import annotations

from app.models.api_schemas import HealthResponse, ServiceMeshStatusResponse
from app.services.service_status import collect_service_status


def health() -> HealthResponse:
    return HealthResponse(status="ok", service="orchestrateur-local")


def service_status() -> ServiceMeshStatusResponse:
    return collect_service_status()
