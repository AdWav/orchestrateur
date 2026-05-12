from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, HTTPException, status

import api.ollama_models as ollama_catalog
import api.ollama_ops as ollama_ops
from api.context import get_runtime_ollama
from api.schemas import (
    ModelWarmUnloadAck,
    OllamaModelsResponse,
    OllamaRuntimeSettingsResponse,
    OllamaRuntimeSettingsUpdate,
)

router = APIRouter(prefix="/v1/runtime/ollama", tags=["runtime-ollama"])


def _require_ollama_settings_backend() -> None:
    if os.getenv("MODEL_BACKEND", "dry-run").lower() != "ollama":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Le routing runtime en direct n'est disponible que lorsque "
                "`MODEL_BACKEND=ollama`. Redefinir puis redemarrer l'API."
            ),
        )


@router.get("/models", response_model=OllamaModelsResponse)
def list_installed_models_endpoint() -> OllamaModelsResponse:
    try:
        return ollama_catalog.fetch_ollama_model_names()
    except httpx.HTTPStatusError as exc:
        detail = (getattr(exc.response, "text", None) or "").strip() or exc.response.reason_phrase
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ollama HTTP {exc.response.status_code}: {detail}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Impossible de joindre Ollama: {exc}",
        ) from exc


@router.get("/settings", response_model=OllamaRuntimeSettingsResponse)
def get_runtime_model_settings() -> OllamaRuntimeSettingsResponse:
    rt = get_runtime_ollama()
    default_model, runners = rt.snapshot()
    from core.pipeline import PIPELINE_STEP_IDS

    pipeline_steps = list(PIPELINE_STEP_IDS)
    return OllamaRuntimeSettingsResponse(
        default_model=default_model,
        runner_models=runners,
        pipeline_steps=pipeline_steps,
        settings_persist_path=str(rt.persistence_path()) if rt.persistence_path() else None,
        ollama_routing_active=os.getenv("MODEL_BACKEND", "dry-run").lower() == "ollama",
    )


@router.put("/settings", response_model=OllamaRuntimeSettingsResponse)
def put_runtime_model_settings(payload: OllamaRuntimeSettingsUpdate) -> OllamaRuntimeSettingsResponse:
    _require_ollama_settings_backend()
    try:
        ollama_ops.validate_models_installed(
            {payload.default_model, *payload.runner_models.values()},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        get_runtime_ollama().apply(
            default_model=payload.default_model,
            runner_models=payload.runner_models,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return get_runtime_model_settings()


@router.post("/models/{model_name}/warm", response_model=ModelWarmUnloadAck)
def warm_installed_model_endpoint(model_name: str) -> ModelWarmUnloadAck:
    normalized = model_name.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de modele vide.")

    installed = ollama_ops.fetch_installed_model_name_set()
    if normalized not in installed:
        detail = ", ".join(sorted(installed)) or "(aucun)"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modele '{normalized}' inconnu parmi les tags Ollama. Disponibles: {detail}.",
        )
    try:
        ollama_ops.warm_model_loaded(normalized)
    except httpx.HTTPStatusError as exc:
        txt = (getattr(exc.response, "text", None) or "").strip() or exc.response.reason_phrase
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Warm Ollama HTTP {exc.response.status_code}: {txt}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Impossible de joindre Ollama pendant le warmup: {exc}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return ModelWarmUnloadAck(model=normalized, action="warm")


@router.post("/models/{model_name}/unload", response_model=ModelWarmUnloadAck)
def unload_installed_model_endpoint(model_name: str) -> ModelWarmUnloadAck:
    normalized = model_name.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de modele vide.")

    installed = ollama_ops.fetch_installed_model_name_set()
    if normalized not in installed:
        detail = ", ".join(sorted(installed)) or "(aucun)"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modele '{normalized}' inconnu parmi les tags Ollama. Disponibles: {detail}.",
        )

    try:
        ollama_ops.unload_model_from_memory(normalized)
    except httpx.HTTPStatusError as exc:
        txt = (getattr(exc.response, "text", None) or "").strip() or exc.response.reason_phrase
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unload Ollama HTTP {exc.response.status_code}: {txt}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Impossible de joindre Ollama pendant l'unload: {exc}",
        ) from exc

    return ModelWarmUnloadAck(model=normalized, action="unload")
