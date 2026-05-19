from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.models.api_schemas import OllamaModelsResponse
from tests.conftest import reload_api_app


def _reload_app(monkeypatch) -> tuple[TestClient, object]:
    monkeypatch.setenv("ORCHESTRATOR_MODE", "local")
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    reloaded = reload_api_app()
    return TestClient(reloaded.app), reloaded


def test_list_ollama_models_returns_sorted_names(monkeypatch) -> None:
    client, reloaded = _reload_app(monkeypatch)

    def fake_fetch() -> OllamaModelsResponse:
        return OllamaModelsResponse(models=["zebra", "alpha"])

    monkeypatch.setattr("app.services.ollama_models.fetch_ollama_model_names", fake_fetch)

    response = client.get("/v1/runtime/ollama/models")
    assert response.status_code == 200
    assert response.json() == {"models": ["zebra", "alpha"]}


def test_list_ollama_models_gateway_error(monkeypatch) -> None:
    client, reloaded = _reload_app(monkeypatch)

    def fake_fetch() -> OllamaModelsResponse:
        raise httpx.ConnectError("simulated")

    monkeypatch.setattr("app.services.ollama_models.fetch_ollama_model_names", fake_fetch)

    response = client.get("/v1/runtime/ollama/models")
    assert response.status_code == 502
    assert "Ollama" in response.json()["detail"]
