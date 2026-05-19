from __future__ import annotations

import os

from app.models.api_schemas import (
    SamplingLiveUpdate,
    SamplingPreviewRequest,
    SamplingPreviewResponse,
    SamplingProfile,
    SamplingSettingsResponse,
)
from app.services import ollama_ops
from app.services.runtime_context import get_runtime_ollama, get_runtime_sampling
from core.sampling_settings import SamplingSnapshot


class SamplingController:
    def get_settings(self) -> SamplingSettingsResponse:
        store = get_runtime_sampling()
        return self._build_response(store)

    def update_live(self, payload: SamplingLiveUpdate) -> SamplingSettingsResponse:
        store = get_runtime_sampling()
        store.apply_live(_snapshot_from_payload(payload))
        return self._build_response(store)

    def preview_live(self, payload: SamplingPreviewRequest) -> SamplingPreviewResponse:
        self._require_ollama_backend()
        model = (payload.model or "").strip() or get_runtime_ollama().default_model()
        if not model:
            raise ValueError("Aucun modele par defaut configure.")
        ollama_ops.validate_models_installed({model})
        prompt = payload.prompt.strip()
        if not prompt:
            raise ValueError("Le prompt ne peut pas etre vide.")

        live_options = get_runtime_sampling().live_snapshot().to_ollama_options()
        num_predict = live_options.pop("num_predict", None) or 96
        parsed = ollama_ops.ollama_post_generate(
            model,
            prompt=prompt,
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
            num_predict=int(num_predict),
            options_override=live_options,
        )
        content = parsed.get("response", "").strip()
        if not content:
            raise RuntimeError(f"Ollama a renvoye une reponse vide pour '{model}'.")
        return SamplingPreviewResponse(
            model=model,
            profile="live",
            content=content,
            backend=f"ollama:{model}",
        )

    @staticmethod
    def _build_response(store) -> SamplingSettingsResponse:
        return SamplingSettingsResponse(
            orchestration=_profile_from_snapshot(store.orchestration_snapshot()),
            live=_profile_from_snapshot(store.live_snapshot()),
            settings_persist_path=str(store.persistence_path()) if store.persistence_path() else None,
            ollama_active=os.getenv("MODEL_BACKEND", "dry-run").lower() == "ollama",
        )

    @staticmethod
    def _require_ollama_backend() -> None:
        if os.getenv("MODEL_BACKEND", "dry-run").lower() != "ollama":
            raise RuntimeError(
                "Le profil live n'est utilisable qu'avec MODEL_BACKEND=ollama."
            )


def _snapshot_from_payload(payload: SamplingLiveUpdate) -> SamplingSnapshot:
    return SamplingSnapshot(
        temperature=payload.temperature,
        top_k=payload.top_k,
        top_p=payload.top_p,
        min_p=payload.min_p,
        mirostat=payload.mirostat,
        mirostat_eta=payload.mirostat_eta,
        mirostat_tau=payload.mirostat_tau,
        presence_penalty=payload.presence_penalty,
        frequency_penalty=payload.frequency_penalty,
        repeat_penalty=payload.repeat_penalty,
        repeat_last_n=payload.repeat_last_n,
        logit_bias=payload.logit_bias,
        stop=payload.stop,
        num_predict=payload.num_predict,
    )


def _profile_from_snapshot(snapshot: SamplingSnapshot) -> SamplingProfile:
    return SamplingProfile(
        temperature=snapshot.temperature,
        top_k=snapshot.top_k,
        top_p=snapshot.top_p,
        min_p=snapshot.min_p,
        mirostat=snapshot.mirostat,
        mirostat_eta=snapshot.mirostat_eta,
        mirostat_tau=snapshot.mirostat_tau,
        presence_penalty=snapshot.presence_penalty,
        frequency_penalty=snapshot.frequency_penalty,
        repeat_penalty=snapshot.repeat_penalty,
        repeat_last_n=snapshot.repeat_last_n,
        logit_bias=snapshot.logit_bias,
        stop=snapshot.stop,
        num_predict=snapshot.num_predict,
    )
