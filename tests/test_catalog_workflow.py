from __future__ import annotations

from pathlib import Path

from core.catalog_bootstrap import ensure_dev_team_catalog
from core.contracts import WorkItem
from core.definition_catalog import FileDefinitionCatalog
from core.orchestrator import MultiAgentOrchestrator


def _repo_catalog() -> Path:
    return Path(__file__).resolve().parents[1] / "catalog"


def _orchestrator(tmp_path) -> MultiAgentOrchestrator:
    catalog = FileDefinitionCatalog(tmp_path)
    ensure_dev_team_catalog(catalog)
    return MultiAgentOrchestrator(catalog=catalog)


def test_catalog_agents_include_split_code_and_integration(tmp_path) -> None:
    catalog = FileDefinitionCatalog(tmp_path)
    ensure_dev_team_catalog(catalog)

    backend = catalog.get_agent("code_backend")
    assert backend.runner_role == "code_backend"

    integration = catalog.get_agent("integration")
    assert "playwright" in integration.mission.lower() or "complet" in integration.mission.lower()

    contract = catalog.get_agent("api_contract")
    assert "contrat" in contract.mission.lower()

    tdd = catalog.get_workflow("team-tdd")
    assert [step.agent_definition_id for step in tdd.steps] == [
        "write_tests",
        "code_backend",
        "code_frontend",
        "integration",
        "run_fix",
        "document",
    ]

    classic = catalog.get_workflow("team-classic")
    assert classic.steps[1].agent_definition_id == "api_contract"
    assert "code_backend" in {s.agent_definition_id for s in classic.steps}


def test_run_catalog_workflow_team_tdd(tmp_path) -> None:
    orchestrator = _orchestrator(tmp_path)
    item = WorkItem(
        objective="Ajouter un validateur de configuration",
        use_case_id="dev-team-benchmark",
    )

    result = orchestrator.run_catalog_workflow("team-tdd", item)

    assert result.verification_passed is True
    assert result.team_id == "team-tdd"
    assert len(result.outputs) == 6
    roles = [output.role for output in result.outputs]
    assert roles == [
        "write_tests",
        "code_backend",
        "code_frontend",
        "integration",
        "run_fix",
        "document",
    ]


def test_backend_and_frontend_runners_are_distinct(tmp_path) -> None:
    from core.agent_runtime import run_agent_request
    from core.contracts import AgentExecutionRequest

    item = WorkItem(objective="Feature X", use_case_id="dev-team-benchmark")
    memory = {"state": {}, "events": []}

    backend = run_agent_request(
        AgentExecutionRequest(role="code_backend", work_item=item, memory=memory)
    )
    memory = backend.memory
    frontend = run_agent_request(
        AgentExecutionRequest(role="code_frontend", work_item=item, memory=memory)
    )

    assert backend.output.role == "code_backend"
    assert "backend" in str(backend.output.artifacts.get("source_files", [])).lower()
    assert frontend.output.role == "code_frontend"
    assert "frontend" in str(frontend.output.artifacts.get("source_files", [])).lower()


def test_documentation_steward_workflow_loaded_from_catalog() -> None:
    catalog = FileDefinitionCatalog(_repo_catalog())
    wf = catalog.get_workflow("documentation-steward")
    assert [step.id for step in wf.steps] == ["doc_inventory", "doc_sync", "doc_qa"]
    assert catalog.get_agent("doc_inventory").id == "doc_inventory"


def test_run_documentation_steward_catalog_workflow() -> None:
    catalog = FileDefinitionCatalog(_repo_catalog())
    orchestrator = MultiAgentOrchestrator(catalog=catalog)
    item = WorkItem(
        objective="Verifier l'alignement docs/docker-stack.md avec les services declares.",
        use_case_id="documentation-steward",
        success_criteria=["Inventaire cite des chemins reels", "Verdict QA explicite"],
    )
    result = orchestrator.run_catalog_workflow("documentation-steward", item)
    assert result.team_id == "documentation-steward"
    assert len(result.outputs) == 3
    assert [out.role for out in result.outputs] == ["generic", "generic", "generic"]
    assert all(out.approved for out in result.outputs)
