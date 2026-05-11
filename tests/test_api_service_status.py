from __future__ import annotations

from importlib import reload

from fastapi.testclient import TestClient

import api.main as api_main
import api.service_status as service_status


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 400


def test_service_status_endpoint_reports_mesh_lights(monkeypatch) -> None:
    monkeypatch.setenv("PLANNER_AGENT_URL", "http://planner-agent:8001")
    monkeypatch.setenv("RESEARCHER_AGENT_URL", "http://researcher-agent:8002")
    monkeypatch.setenv("EXECUTOR_AGENT_URL", "http://executor-agent:8003")
    monkeypatch.setenv("VERIFIER_AGENT_URL", "http://verifier-agent:8004")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")

    def fake_get(url: str, timeout: float) -> _Response:
        if "researcher-agent" in url or "ollama" in url:
            return _Response(503)
        return _Response(200)

    monkeypatch.setattr(service_status.httpx, "get", fake_get)

    reloaded = reload(api_main)
    client = TestClient(reloaded.app)

    response = client.get("/v1/services/status")

    assert response.status_code == 200
    payload = response.json()
    assert [service["label"] for service in payload["services"]] == [
        "PO",
        "Planner",
        "Researcher",
        "Executor",
        "Verifier",
        "Ollama",
    ]
    assert payload["services"][0]["active"] is True
    assert payload["services"][2]["active"] is False
    assert payload["services"][5]["active"] is False
