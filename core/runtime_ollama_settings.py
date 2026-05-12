from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from core.pipeline import PIPELINE_STEP_IDS


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value else default


def _runner_model_env_for_step(step_id: str, fallback: str) -> str:
    primary = _env(f"OLLAMA_MODEL_{step_id.upper()}")
    if primary:
        return primary
    legacy_suffix = {
        "plan": "PLANNER",
        "research": "RESEARCHER",
        "execute": "EXECUTOR",
        "verify": "VERIFIER",
    }.get(step_id)
    if legacy_suffix:
        legacy_val = _env(f"OLLAMA_MODEL_{legacy_suffix}")
        if legacy_val:
            return legacy_val
    return fallback


class RuntimeOllamaSettings:
    """Reglages runtime modèle Ollama (defaut + un modele par etape pipeline), optionnellement persists sur JSON."""

    def __init__(self, persistence_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._persistence_path = persistence_path
        self._default_model = ""
        self._runner_models: dict[str, str] = {}

    @classmethod
    def bootstrap_from_environment(cls, persistence_path: Path | None = None) -> RuntimeOllamaSettings:
        path = persistence_path or _persist_path_from_env()
        store = cls(persistence_path=path)

        env_default_raw = (_env("OLLAMA_DEFAULT_MODEL", "qwen2.5:0.5b") or "qwen2.5:0.5b").strip()

        persisted_default: str | None = None
        persisted_runners: dict[str, str] = {}
        if path is not None and path.is_file():
            try:
                payload_raw = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                payload_raw = None
            if isinstance(payload_raw, dict):
                d = payload_raw.get("default_model")
                if isinstance(d, str) and d.strip():
                    persisted_default = d.strip()
                br = payload_raw.get("runner_models")
                if isinstance(br, dict):
                    for sid in PIPELINE_STEP_IDS:
                        v = br.get(sid)
                        if isinstance(v, str) and v.strip():
                            persisted_runners[sid] = v.strip()

        resolved_default = (persisted_default or env_default_raw).strip()

        runners: dict[str, str] = {}
        for step_id in PIPELINE_STEP_IDS:
            if step_id in persisted_runners:
                runners[step_id] = persisted_runners[step_id]
            else:
                runners[step_id] = _runner_model_env_for_step(step_id, resolved_default)

        with store._lock:
            store._default_model = resolved_default
            store._runner_models = runners
        return store

    def persistence_path(self) -> Path | None:
        return self._persistence_path

    def default_model(self) -> str:
        with self._lock:
            return self._default_model

    def runner_models(self) -> dict[str, str]:
        with self._lock:
            return dict(self._runner_models)

    def model_for_runner(self, runner_key: str) -> str:
        step_id = runner_key.strip()
        with self._lock:
            mapped = self._runner_models.get(step_id)
            if mapped and mapped.strip():
                return mapped.strip()
            return self._default_model

    def snapshot(self) -> tuple[str, dict[str, str]]:
        with self._lock:
            return self._default_model, dict(self._runner_models)

    def apply(
        self,
        *,
        default_model: str,
        runner_models: dict[str, str],
    ) -> None:
        default_clean = default_model.strip()
        if not default_clean:
            raise ValueError("default_model ne peut pas etre vide.")
        runners: dict[str, str] = {}
        for sid in PIPELINE_STEP_IDS:
            val = runner_models.get(sid, "").strip()
            runners[sid] = val if val else default_clean
        with self._lock:
            self._default_model = default_clean
            self._runner_models = runners
            self._save_locked()

    def _save_locked(self) -> None:
        if self._persistence_path is None:
            return
        payload = {"default_model": self._default_model, "runner_models": dict(self._runner_models)}
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        self._persistence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _persist_path_from_env() -> Path | None:
    raw = os.getenv("ORCHESTRATOR_RUNTIME_SETTINGS_PATH")
    if not raw:
        raw = os.getenv("ORCHESTRATOR_RUNTIME_OLLAMA_SETTINGS_PATH")
    if not raw or not raw.strip():
        return None
    return Path(raw.strip())


def reset_runtime_settings_for_tests(store: RuntimeOllamaSettings, *, default: str, runners: dict[str, str]) -> None:
    with store._lock:
        store._default_model = default
        store._runner_models = {sid: runners.get(sid, default) for sid in PIPELINE_STEP_IDS}

