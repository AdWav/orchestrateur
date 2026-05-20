from __future__ import annotations

import json
import os
from collections.abc import Iterator

from app.models.api_schemas import (
    ModelTokenPiece,
    SamplingLiveUpdate,
    SamplingPreviewRequest,
    SamplingPreviewResponse,
    SamplingProfile,
    SamplingSettingsResponse,
    SamplingTokenizeCapabilitiesResponse,
    SamplingTokenizeRequest,
    SamplingTokenizeResponse,
)
from app.services import ollama_ops
from app.services.ollama_tokenize import (
    ModelTokenizeUnavailable,
    tokenize_capabilities,
    tokenize_model_text,
)
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

    def _preview_live_context(self, payload: SamplingPreviewRequest) -> tuple[str, str, dict, int]:
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
        return model, prompt, live_options, int(num_predict)

    def preview_live(self, payload: SamplingPreviewRequest) -> SamplingPreviewResponse:
        model, prompt, live_options, num_predict = self._preview_live_context(payload)
        parsed = ollama_ops.ollama_post_generate(
            model,
            prompt=prompt,
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
            num_predict=num_predict,
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

    def tokenize_capabilities(self) -> SamplingTokenizeCapabilitiesResponse:
        self._require_ollama_backend()
        caps = tokenize_capabilities()
        return SamplingTokenizeCapabilitiesResponse(
            ollama_api=bool(caps["ollama_api"]),
            llama_cpp=bool(caps["llama_cpp"]),
            source=caps["source"],  # type: ignore[arg-type]
        )

    def tokenize_text(self, payload: SamplingTokenizeRequest) -> SamplingTokenizeResponse:
        self._require_ollama_backend()
        model = (payload.model or "").strip() or get_runtime_ollama().default_model()
        if not model:
            raise ValueError("Aucun modele par defaut configure.")
        try:
            result = tokenize_model_text(model, payload.text)
        except ModelTokenizeUnavailable as exc:
            raise RuntimeError(str(exc)) from exc
        tokens = [
            ModelTokenPiece(id=piece.id, text=piece.text) for piece in result.tokens
        ]
        return SamplingTokenizeResponse(
            model=result.model,
            source=result.source,
            token_count=len(tokens),
            tokens=tokens,
        )

    def preview_live_stream(self, payload: SamplingPreviewRequest) -> Iterator[str]:
        model, prompt, live_options, num_predict = self._preview_live_context(payload)
        content_parts: list[str] = []
        final_payload: dict | None = None

        for chunk in ollama_ops.iter_ollama_post_generate(
            model,
            prompt=prompt,
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
            num_predict=num_predict,
            options_override=live_options,
        ):
            token = chunk.get("response")
            if isinstance(token, str) and token:
                content_parts.append(token)
                yield self._stream_event("token", content=token)
            if chunk.get("done"):
                final_payload = chunk

        content = "".join(content_parts).strip()
        if not content:
            raise RuntimeError(f"Ollama a renvoye une reponse vide pour '{model}'.")

        stats = self._stream_stats(final_payload or {})
        yield self._stream_event(
            "done",
            model=model,
            profile="live",
            backend=f"ollama:{model}",
            content=content,
            stats=stats,
        )

    @staticmethod
    def _stream_event(event: str, **fields) -> str:
        return json.dumps({"event": event, **fields}, ensure_ascii=False) + "\n"

    @staticmethod
    def _stream_stats(payload: dict) -> dict[str, int | float]:
        keys = (
            "total_duration",
            "load_duration",
            "prompt_eval_count",
            "prompt_eval_duration",
            "eval_count",
            "eval_duration",
        )
        stats: dict[str, int | float] = {}
        for key in keys:
            value = payload.get(key)
            if isinstance(value, (int, float)):
                stats[key] = value
        return stats

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
