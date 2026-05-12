from __future__ import annotations

from importlib import reload

import httpx
from fastapi.testclient import TestClient

import api.main as api_main
from api.schemas import OllamaModelsResponse


def _reload_app(monkeypatch) -> TestClient:
    monkeypatch.setenv("ORCHESTRATOR_MODE", "local")
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    reloaded = reload(api_main)
    return TestClient(reloaded.app), reloaded


def test_list_ollama_models_returns_sorted_names(monkeypatch) -> None:
    client, reloaded = _reload_app(monkeypatch)

    def fake_fetch() -> OllamaModelsResponse:
        return OllamaModelsResponse(models=["zebra", "alpha"])

    monkeypatch.setattr("api.ollama_models.fetch_ollama_model_names", fake_fetch)

    response = client.get("/runtime/ollama/models")
    assert response.status_code == 200
    assert response.json() == {"models": ["zebra", "alpha"]}


def test_list_ollama_models_gateway_error(monkeypatch) -> None:
    client, reloaded = _reload_app(monkeypatch)

    def fake_fetch() -> OllamaModelsResponse:
        raise httpx.ConnectError("simulated")

    monkeypatch.setattr("api.ollama_models.fetch_ollama_model_names", fake_fetch)

    response = client.get("/runtime/ollama/models")
    assert response.status_code == 502
    assert "Ollama" in response.json()["detail"]
