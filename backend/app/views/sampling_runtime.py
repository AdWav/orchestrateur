from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.controllers.ollama_runtime_controller import OllamaRuntimeController
from app.controllers.sampling_controller import SamplingController
from app.dependencies import get_container
from app.models.api_schemas import (
    SamplingLiveUpdate,
    SamplingPreviewRequest,
    SamplingPreviewResponse,
    SamplingSettingsResponse,
    SamplingTokenizeCapabilitiesResponse,
    SamplingTokenizeRequest,
    SamplingTokenizeResponse,
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


@router.get("/tokenize/capabilities", response_model=SamplingTokenizeCapabilitiesResponse)
def sampling_tokenize_capabilities() -> SamplingTokenizeCapabilitiesResponse:
    try:
        return _controller().tokenize_capabilities()
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post("/tokenize", response_model=SamplingTokenizeResponse)
def sampling_tokenize_text(payload: SamplingTokenizeRequest) -> SamplingTokenizeResponse:
    try:
        return _controller().tokenize_text(payload)
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post("/preview/stream")
def preview_live_sampling_stream(payload: SamplingPreviewRequest) -> StreamingResponse:
    try:
        stream = _controller().preview_live_stream(payload)
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc

    return StreamingResponse(stream, media_type="application/x-ndjson")
