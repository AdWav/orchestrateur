from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.controllers.ollama_runtime_controller import OllamaRuntimeController
from app.controllers.sampling_controller import SamplingController
from app.dependencies import get_container
from app.models.api_schemas import (
    SamplingLiveUpdate,
    SamplingPreviewRequest,
    SamplingPreviewResponse,
    SamplingSettingsResponse,
)

router = APIRouter(prefix="/v1/runtime/sampling", tags=["runtime-sampling"])


def _controller() -> SamplingController:
    return get_container().sampling_controller


@router.get("/settings", response_model=SamplingSettingsResponse)
def get_sampling_settings() -> SamplingSettingsResponse:
    return _controller().get_settings()


@router.put("/settings/live", response_model=SamplingSettingsResponse)
def put_live_sampling_settings(payload: SamplingLiveUpdate) -> SamplingSettingsResponse:
    return _controller().update_live(payload)


@router.post("/preview", response_model=SamplingPreviewResponse)
def preview_live_sampling(payload: SamplingPreviewRequest) -> SamplingPreviewResponse:
    try:
        return _controller().preview_live(payload)
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc
