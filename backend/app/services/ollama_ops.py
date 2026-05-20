from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

import httpx

from app.config.settings import ollama_base_url
from core.sampling_context import orchestration_sampling_options


def _env_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def fetch_installed_model_names(timeout_seconds: float = 15.0) -> list[str]:
    base = ollama_base_url().rstrip("/")
    response = httpx.get(f"{base}/api/tags", timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("models") or []
    names: list[str] = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("name"), str):
            names.append(row["name"])
    return sorted(names)


def fetch_installed_model_name_set(timeout_seconds: float = 15.0) -> frozenset[str]:
    return frozenset(fetch_installed_model_names(timeout_seconds))


def validate_models_installed(names: set[str]) -> None:
    if not names:
        return
    installed = fetch_installed_model_name_set()
    missing = sorted(n for n in names if n not in installed)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Modele(s) absent(s) d'Ollama: {joined}. Utiliser les noms depuis /api/tags.")


def _generate_request_body(
    model: str,
    *,
    prompt: str,
    keep_alive: str | int,
    num_predict: int,
    stream: bool,
    options_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_options = (
        dict(options_override) if options_override is not None else orchestration_sampling_options()
    )
    options = {**base_options, "num_predict": num_predict}
    return {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": keep_alive,
        "options": options,
    }


def _generate_timeout_seconds(timeout_seconds: float | None) -> float:
    return timeout_seconds if timeout_seconds is not None else _env_float("OLLAMA_TIMEOUT_SECONDS", "120")


def iter_ollama_post_generate(
    model: str,
    *,
    prompt: str,
    keep_alive: str | int,
    num_predict: int,
    timeout_seconds: float | None = None,
    options_override: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    base = ollama_base_url().rstrip("/")
    body = _generate_request_body(
        model,
        prompt=prompt,
        keep_alive=keep_alive,
        num_predict=num_predict,
        stream=True,
        options_override=options_override,
    )
    with httpx.stream(
        "POST",
        f"{base}/api/generate",
        json=body,
        timeout=_generate_timeout_seconds(timeout_seconds),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                yield parsed


def ollama_post_generate(
    model: str,
    *,
    prompt: str,
    keep_alive: str | int,
    num_predict: int,
    timeout_seconds: float | None = None,
    options_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = ollama_base_url().rstrip("/")
    body = _generate_request_body(
        model,
        prompt=prompt,
        keep_alive=keep_alive,
        num_predict=num_predict,
        stream=False,
        options_override=options_override,
    )
    response = httpx.post(
        f"{base}/api/generate",
        json=body,
        timeout=_generate_timeout_seconds(timeout_seconds),
    )
    response.raise_for_status()
    parsed = response.json()
    return parsed if isinstance(parsed, dict) else {}


def warm_model_loaded(model: str) -> dict[str, Any]:
    keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "5m")
    predict = max(1, _env_int("OLLAMA_NUM_PREDICT", "96") // 4)
    payload = ollama_post_generate(
        model,
        prompt="Warmup orchestrateur.",
        keep_alive=keep_alive,
        num_predict=predict,
    )
    content = payload.get("response") or ""
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"Warm Ollama: reponse vide pour le modele '{model}'.")
    return {"detail": content.strip(), "payload": payload}


def unload_model_from_memory(model: str) -> None:
    keep_alive_seconds = os.getenv("OLLAMA_UNLOAD_KEEP_ALIVE", "0")
    try:
        keep_alive_final: str | int = int(keep_alive_seconds)
    except ValueError:
        keep_alive_final = keep_alive_seconds
    ollama_post_generate(
        model,
        prompt=".",
        keep_alive=keep_alive_final,
        num_predict=1,
    )
