from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import reload_api_app


def test_repo_audit_endpoint_returns_structured_report(tmp_path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nRepo overview.\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_TOKEN=\n", encoding="utf-8")

    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    reloaded = reload_api_app()
    client = TestClient(reloaded.app)

    response = client.post(
        "/workflows/repo-audit",
        json={
            "objective": "Auditer ce depot en lecture seule",
            "repo_path": str(tmp_path),
            "analysis_axes": ["docs", "dependencies", "security"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request"]["use_case_id"] == "local-repo-audit"
    assert Path(payload["inventory"]["root_path"]).resolve() == tmp_path.resolve()
    assert payload["outputs"][0]["role"] == "plan"
    assert payload["validation_report"]["approved"] is True
