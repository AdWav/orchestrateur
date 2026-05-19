from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.controllers.ollama_runtime_controller import OllamaRuntimeController
from app.dependencies import get_container
from app.models.api_schemas import (
    ModelWarmUnloadAck,
    OllamaModelsResponse,
    OllamaRuntimeSettingsResponse,
    OllamaRuntimeSettingsUpdate,
)

router = APIRouter(prefix="/v1/runtime/ollama", tags=["runtime-ollama"])


def _controller() -> OllamaRuntimeController:
    return get_container().ollama_runtime_controller


@router.get("/models", response_model=OllamaModelsResponse)
def list_installed_models_endpoint() -> OllamaModelsResponse:
    try:
        return _controller().list_models()
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/settings", response_model=OllamaRuntimeSettingsResponse)
def get_runtime_model_settings() -> OllamaRuntimeSettingsResponse:
    return _controller().get_settings()


@router.put("/settings", response_model=OllamaRuntimeSettingsResponse)
def put_runtime_model_settings(payload: OllamaRuntimeSettingsUpdate) -> OllamaRuntimeSettingsResponse:
    try:
        return _controller().update_settings(payload)
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post("/models/{model_name}/warm", response_model=ModelWarmUnloadAck)
def warm_installed_model_endpoint(model_name: str) -> ModelWarmUnloadAck:
    try:
        return _controller().warm_model(model_name)
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post("/models/{model_name}/unload", response_model=ModelWarmUnloadAck)
def unload_installed_model_endpoint(model_name: str) -> ModelWarmUnloadAck:
    try:
        return _controller().unload_model(model_name)
    except Exception as exc:
        code, detail = OllamaRuntimeController.map_http_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc
