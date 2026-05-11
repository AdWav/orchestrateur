from __future__ import annotations

from importlib import reload

from fastapi.testclient import TestClient

import api.main as api_main


def test_health_endpoint_accepts_vite_origin(monkeypatch) -> None:
    monkeypatch.delenv("UI_ALLOWED_ORIGINS", raising=False)
    reloaded = reload(api_main)
    client = TestClient(reloaded.app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
