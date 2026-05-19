from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value else default


def _env_optional_float(name: str) -> float | None:
    raw = _env(name)
    if not raw:
        return None
    return float(raw)


def _env_optional_int(name: str) -> int | None:
    raw = _env(name)
    if not raw:
        return None
    return int(raw)


@dataclass(slots=True)
class SamplingSnapshot:
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    min_p: float | None = None
    mirostat: int | None = None
    mirostat_eta: float | None = None
    mirostat_tau: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    repeat_penalty: float | None = None
    repeat_last_n: int | None = None
    logit_bias: dict[str, float] | None = None
    stop: list[str] | None = None
    num_predict: int | None = None

    def to_ollama_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.top_k is not None:
            options["top_k"] = self.top_k
        if self.top_p is not None:
            options["top_p"] = self.top_p
        if self.min_p is not None:
            options["min_p"] = self.min_p
        if self.mirostat is not None:
            options["mirostat"] = self.mirostat
        if self.mirostat_eta is not None:
            options["mirostat_eta"] = self.mirostat_eta
        if self.mirostat_tau is not None:
            options["mirostat_tau"] = self.mirostat_tau
        if self.presence_penalty is not None:
            options["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty is not None:
            options["frequency_penalty"] = self.frequency_penalty
        if self.repeat_penalty is not None:
            options["repeat_penalty"] = self.repeat_penalty
        if self.repeat_last_n is not None:
            options["repeat_last_n"] = self.repeat_last_n
        if self.logit_bias:
            options["logit_bias"] = self.logit_bias
        if self.stop:
            options["stop"] = self.stop
        if self.num_predict is not None:
            options["num_predict"] = self.num_predict
        return options


class RuntimeSamplingSettings:
    """Deux profils sur le meme modele Ollama : orchestration (fige) et live (modifiable a chaud)."""

    def __init__(self, persistence_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._persistence_path = persistence_path
        self._orchestration = SamplingSnapshot()
        self._live = SamplingSnapshot()

    @classmethod
    def bootstrap_from_environment(cls, persistence_path: Path | None = None) -> RuntimeSamplingSettings:
        path = persistence_path or _persist_path_from_env()
        store = cls(persistence_path=path)
        orchestration = _snapshot_from_environment()

        persisted_live: dict[str, Any] | None = None
        if path is not None and path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raw = None
            if isinstance(raw, dict):
                live_block = raw.get("live")
                if isinstance(live_block, dict):
                    persisted_live = live_block
                else:
                    persisted_live = raw

        live = _snapshot_from_mapping(persisted_live) if persisted_live else replace(orchestration)

        with store._lock:
            store._orchestration = orchestration
            store._live = live
        return store

    def persistence_path(self) -> Path | None:
        return self._persistence_path

    def orchestration_snapshot(self) -> SamplingSnapshot:
        with self._lock:
            return replace(self._orchestration)

    def live_snapshot(self) -> SamplingSnapshot:
        with self._lock:
            return replace(self._live)

    def apply_live(self, payload: SamplingSnapshot) -> None:
        with self._lock:
            self._live = payload
            self._save_live_locked()

    def _save_live_locked(self) -> None:
        if self._persistence_path is None:
            return
        payload = {"live": _mapping_from_snapshot(self._live)}
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        self._persistence_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _snapshot_from_environment() -> SamplingSnapshot:
    stop_raw = _env("OLLAMA_STOP")
    stop = [part.strip() for part in stop_raw.split(",") if part.strip()] if stop_raw else None
    return SamplingSnapshot(
        temperature=_env_optional_float("OLLAMA_TEMPERATURE") if _env("OLLAMA_TEMPERATURE") else 0.2,
        top_k=_env_optional_int("OLLAMA_TOP_K"),
        top_p=_env_optional_float("OLLAMA_TOP_P"),
        min_p=_env_optional_float("OLLAMA_MIN_P"),
        mirostat=_env_optional_int("OLLAMA_MIROSTAT"),
        mirostat_eta=_env_optional_float("OLLAMA_MIROSTAT_ETA"),
        mirostat_tau=_env_optional_float("OLLAMA_MIROSTAT_TAU"),
        presence_penalty=_env_optional_float("OLLAMA_PRESENCE_PENALTY"),
        frequency_penalty=_env_optional_float("OLLAMA_FREQUENCY_PENALTY"),
        repeat_penalty=_env_optional_float("OLLAMA_REPEAT_PENALTY"),
        repeat_last_n=_env_optional_int("OLLAMA_REPEAT_LAST_N"),
        logit_bias=None,
        stop=stop,
        num_predict=int(_env("OLLAMA_NUM_PREDICT", "96")) if _env("OLLAMA_NUM_PREDICT", "96") else 96,
    )


def _snapshot_from_mapping(payload: dict[str, Any]) -> SamplingSnapshot:
    logit_bias = payload.get("logit_bias")
    parsed_bias: dict[str, float] | None = None
    if isinstance(logit_bias, dict):
        parsed_bias = {}
        for key, value in logit_bias.items():
            if isinstance(key, str) and isinstance(value, (int, float)):
                parsed_bias[key] = float(value)

    stop = payload.get("stop")
    parsed_stop: list[str] | None = None
    if isinstance(stop, list):
        parsed_stop = [str(item).strip() for item in stop if str(item).strip()]

    def _opt_float(key: str) -> float | None:
        value = payload.get(key)
        if value is None:
            return None
        return float(value)

    def _opt_int(key: str) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        return int(value)

    return SamplingSnapshot(
        temperature=_opt_float("temperature"),
        top_k=_opt_int("top_k"),
        top_p=_opt_float("top_p"),
        min_p=_opt_float("min_p"),
        mirostat=_opt_int("mirostat"),
        mirostat_eta=_opt_float("mirostat_eta"),
        mirostat_tau=_opt_float("mirostat_tau"),
        presence_penalty=_opt_float("presence_penalty"),
        frequency_penalty=_opt_float("frequency_penalty"),
        repeat_penalty=_opt_float("repeat_penalty"),
        repeat_last_n=_opt_int("repeat_last_n"),
        logit_bias=parsed_bias,
        stop=parsed_stop,
        num_predict=_opt_int("num_predict"),
    )


def _mapping_from_snapshot(snapshot: SamplingSnapshot) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in SamplingSnapshot.__dataclass_fields__:
        value = getattr(snapshot, field)
        if value is not None:
            payload[field] = value
    return payload


def _persist_path_from_env() -> Path | None:
    raw = os.getenv("ORCHESTRATOR_LIVE_SAMPLING_SETTINGS_PATH") or os.getenv(
        "ORCHESTRATOR_DECODING_SETTINGS_PATH",
    )
    if not raw or not raw.strip():
        return None
    return Path(raw.strip())


def reset_sampling_settings_for_tests(
    store: RuntimeSamplingSettings,
    *,
    orchestration: SamplingSnapshot,
    live: SamplingSnapshot,
) -> None:
    with store._lock:
        store._orchestration = orchestration
        store._live = live
