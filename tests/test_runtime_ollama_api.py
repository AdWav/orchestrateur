from __future__ import annotations

from importlib import reload

from fastapi.testclient import TestClient

import api.main as api_main
from core.pipeline import PIPELINE_STEP_IDS


def test_get_runtime_ollama_settings_exposes_pipeline(monkeypatch) -> None:
    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    reloaded = reload(api_main)
    client = TestClient(reloaded.app)

    response = client.get("/v1/runtime/ollama/settings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline_steps"] == list(PIPELINE_STEP_IDS)
    assert isinstance(payload["runner_models"], dict)
    assert payload["ollama_routing_active"] is False


def test_put_runtime_ollama_settings_requires_ollama_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    monkeypatch.setenv("ORCHESTRATOR_RUNTIME_SETTINGS_PATH", str(tmp_path / "rt.json"))
    reloaded = reload(api_main)
    client = TestClient(reloaded.app)

    body = {
        "default_model": "dummy",
        "runner_models": {sid: "dummy" for sid in PIPELINE_STEP_IDS},
    }

    response = client.put("/v1/runtime/ollama/settings", json=body)

    assert response.status_code == 503


def test_put_runtime_ollama_settings_updates_when_models_exist(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    monkeypatch.setenv("MODEL_BACKEND", "ollama")
    monkeypatch.setenv("ORCHESTRATOR_RUNTIME_SETTINGS_PATH", str(tmp_path / "rt.json"))
    monkeypatch.setattr(
        "api.ollama_ops.fetch_installed_model_name_set",
        lambda timeout_seconds=15.0: frozenset({"alpha", "beta"}),
    )

    reloaded = reload(api_main)
    client = TestClient(reloaded.app)

    body = {
        "default_model": "alpha",
        "runner_models": {sid: "beta" if sid != "plan" else "alpha" for sid in PIPELINE_STEP_IDS},
    }

    response = client.put("/v1/runtime/ollama/settings", json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_model"] == "alpha"
    assert payload["runner_models"]["verify"] == "beta"


def test_put_runtime_rejects_unknown_model_tag(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    monkeypatch.setenv("MODEL_BACKEND", "ollama")
    monkeypatch.setattr(
        "api.ollama_ops.fetch_installed_model_name_set",
        lambda timeout_seconds=15.0: frozenset({"alpha"}),
    )

    reloaded = reload(api_main)
    client = TestClient(reloaded.app)

    body = {
        "default_model": "missing",
        "runner_models": {sid: "alpha" for sid in PIPELINE_STEP_IDS},
    }

    response = client.put("/v1/runtime/ollama/settings", json=body)

    assert response.status_code == 400


def test_post_warm_happy_path(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    monkeypatch.setattr(
        "api.ollama_ops.fetch_installed_model_name_set",
        lambda timeout_seconds=15.0: frozenset({"alpha"}),
    )
    monkeypatch.setattr("api.ollama_ops.warm_model_loaded", lambda name: {})

    reloaded = reload(api_main)
    client = TestClient(reloaded.app)

    response = client.post("/v1/runtime/ollama/models/alpha/warm")

    assert response.status_code == 200
    assert response.json() == {"model": "alpha", "action": "warm"}
