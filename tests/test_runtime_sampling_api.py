from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import reload_api_app


def test_get_sampling_settings_exposes_dual_profiles(monkeypatch) -> None:
    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    reloaded = reload_api_app()
    client = TestClient(reloaded.app)

    response = client.get("/v1/runtime/sampling/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["orchestration"]["temperature"] == 0.2
    assert payload["orchestration"]["num_predict"] == 96
    assert payload["live"]["temperature"] == 0.2
    assert payload["ollama_active"] is False


def test_put_live_sampling_does_not_change_orchestration(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    monkeypatch.setenv("ORCHESTRATOR_LIVE_SAMPLING_SETTINGS_PATH", str(tmp_path / "live.json"))
    reloaded = reload_api_app()
    client = TestClient(reloaded.app)

    body = {"temperature": 0.9, "top_p": 0.85}

    response = client.put("/v1/runtime/sampling/settings/live", json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["live"]["temperature"] == 0.9
    assert payload["live"]["top_p"] == 0.85
    assert payload["orchestration"]["temperature"] == 0.2
