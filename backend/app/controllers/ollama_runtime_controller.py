from __future__ import annotations

import os

import httpx

from app.models.api_schemas import (
    ModelWarmUnloadAck,
    OllamaModelsResponse,
    OllamaRuntimeSettingsResponse,
    OllamaRuntimeSettingsUpdate,
)
from app.services import ollama_models, ollama_ops
from app.services.runtime_context import get_runtime_ollama
from core.pipeline import RUNNER_STEP_IDS


class OllamaRuntimeController:
    def list_models(self) -> OllamaModelsResponse:
        return ollama_models.fetch_ollama_model_names()

    def get_settings(self) -> OllamaRuntimeSettingsResponse:
        rt = get_runtime_ollama()
        default_model, runners = rt.snapshot()
        return OllamaRuntimeSettingsResponse(
            default_model=default_model,
            runner_models=runners,
            pipeline_steps=list(RUNNER_STEP_IDS),
            settings_persist_path=str(rt.persistence_path()) if rt.persistence_path() else None,
            ollama_routing_active=os.getenv("MODEL_BACKEND", "dry-run").lower() == "ollama",
        )

    def update_settings(self, payload: OllamaRuntimeSettingsUpdate) -> OllamaRuntimeSettingsResponse:
        self._require_ollama_backend()
        ollama_ops.validate_models_installed(
            {payload.default_model, *payload.runner_models.values()},
        )
        get_runtime_ollama().apply(
            default_model=payload.default_model,
            runner_models=payload.runner_models,
        )
        return self.get_settings()

    def warm_model(self, model_name: str) -> ModelWarmUnloadAck:
        normalized = model_name.strip()
        if not normalized:
            raise ValueError("Nom de modele vide.")
        installed = ollama_ops.fetch_installed_model_name_set()
        if normalized not in installed:
            detail = ", ".join(sorted(installed)) or "(aucun)"
            raise ValueError(
                f"Modele '{normalized}' inconnu parmi les tags Ollama. Disponibles: {detail}."
            )
        ollama_ops.warm_model_loaded(normalized)
        return ModelWarmUnloadAck(model=normalized, action="warm")

    def unload_model(self, model_name: str) -> ModelWarmUnloadAck:
        normalized = model_name.strip()
        if not normalized:
            raise ValueError("Nom de modele vide.")
        installed = ollama_ops.fetch_installed_model_name_set()
        if normalized not in installed:
            detail = ", ".join(sorted(installed)) or "(aucun)"
            raise ValueError(
                f"Modele '{normalized}' inconnu parmi les tags Ollama. Disponibles: {detail}."
            )
        ollama_ops.unload_model_from_memory(normalized)
        return ModelWarmUnloadAck(model=normalized, action="unload")

    @staticmethod
    def _require_ollama_backend() -> None:
        if os.getenv("MODEL_BACKEND", "dry-run").lower() != "ollama":
            raise RuntimeError(
                "Le routing runtime en direct n'est disponible que lorsque MODEL_BACKEND=ollama."
            )

    @staticmethod
    def map_http_error(exc: Exception) -> tuple[int, str]:
        if isinstance(exc, ValueError):
            return 400, str(exc)
        if isinstance(exc, RuntimeError):
            return 503, str(exc)
        if isinstance(exc, httpx.HTTPStatusError):
            detail = (getattr(exc.response, "text", None) or "").strip() or exc.response.reason_phrase
            return 502, f"Ollama HTTP {exc.response.status_code}: {detail}"
        if isinstance(exc, httpx.RequestError):
            return 502, f"Impossible de joindre Ollama: {exc}"
        return 500, str(exc)
