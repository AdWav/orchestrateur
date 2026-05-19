from __future__ import annotations

import httpx

from app.config.settings import ollama_base_url
from app.models.api_schemas import OllamaModelsResponse


def fetch_ollama_model_names(timeout_seconds: float = 10.0) -> OllamaModelsResponse:
    base = ollama_base_url().rstrip("/")
    response = httpx.get(f"{base}/api/tags", timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("models") or []
    names: list[str] = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("name"), str):
            names.append(row["name"])
    names.sort()
    return OllamaModelsResponse(models=names)
