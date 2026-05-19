from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import reload_api_app


def _agent_payload(agent_id: str) -> dict[str, object]:
    return {
        "id": agent_id,
        "name": agent_id.replace("-", " ").title(),
        "business_role": agent_id.replace("-", " ").title(),
        "mission": f"Mission for {agent_id}.",
        "capabilities": [],
        "inputs": [],
        "outputs": [],
        "guardrails": [],
    }


def test_definition_endpoints_create_and_list_presets(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_CATALOG_ROOT", str(tmp_path))
    monkeypatch.setenv("CATALOG_BACKEND", "file")
    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    reloaded = reload_api_app()
    client = TestClient(reloaded.app)

    for agent_id in ("director", "analyst", "delivery", "quality"):
        response = client.post("/definitions/agents", json=_agent_payload(agent_id))
        assert response.status_code == 201

    workflow_response = client.post(
        "/definitions/workflows",
        json={
            "id": "deal-review",
            "name": "Deal review",
            "goal": "Produire un dossier de decision.",
            "context": {"company": "Northbridge Capital"},
            "constraints": ["Rester lisible pour un comite."],
            "success_criteria": ["Le dossier doit etre verifiable."],
            "steps": [
                {
                    "id": "scope",
                    "name": "Scope",
                    "agent_definition_id": "director",
                    "objective": "Cadrer la revue.",
                },
                {
                    "id": "analysis",
                    "name": "Analysis",
                    "agent_definition_id": "analyst",
                    "objective": "Evaluer les risques.",
                    "depends_on": ["scope"],
                },
                {
                    "id": "integration",
                    "name": "Integration",
                    "agent_definition_id": "delivery",
                    "objective": "Preparer le plan d'integration.",
                    "depends_on": ["analysis"],
                },
                {
                    "id": "decision",
                    "name": "Decision",
                    "agent_definition_id": "quality",
                    "objective": "Valider la recommandation.",
                    "depends_on": ["integration"],
                },
            ],
        },
    )

    assert workflow_response.status_code == 201

    listed_agents = client.get("/definitions/agents")
    listed_workflows = client.get("/definitions/workflows")

    assert listed_agents.status_code == 200
    assert listed_workflows.status_code == 200
    agent_ids = {agent["id"] for agent in listed_agents.json()}
    assert {"director", "analyst", "delivery", "quality"} <= agent_ids
    assert {
        "schematic",
        "code",
        "code_backend",
        "code_frontend",
        "api_contract",
        "integration",
        "write_tests",
        "test_and_verify",
        "run_fix",
        "document",
        "security",
        "review",
        "database",
        "devops",
    } <= agent_ids
    assert listed_workflows.json()[0]["id"] == "deal-review"
