from __future__ import annotations

from fastapi.testclient import TestClient

from core.catalog_bootstrap import ensure_dev_team_catalog
from core.contracts import WorkItem
from core.definition_catalog import FileDefinitionCatalog
from core.dev_teams import DEV_TEAM_BENCHMARK_ORDER
from core.orchestrator import MultiAgentOrchestrator
from tests.conftest import reload_api_app


def _orchestrator(tmp_path) -> MultiAgentOrchestrator:
    catalog = FileDefinitionCatalog(tmp_path)
    ensure_dev_team_catalog(catalog)
    return MultiAgentOrchestrator(catalog=catalog)


def test_dev_team_specifications_expose_catalog_roles(tmp_path) -> None:
    orchestrator = _orchestrator(tmp_path)

    tdd = orchestrator.team_specification("team-tdd")
    classic = orchestrator.team_specification("team-classic")

    assert tdd.id == "team-tdd"
    assert [role.role for role in tdd.roles] == [
        "write_tests",
        "code_backend",
        "code_frontend",
        "integration",
        "run_fix",
        "document",
    ]
    assert tdd.methodology == "test-driven-development"

    assert classic.id == "team-classic"
    assert "api_contract" in [role.role for role in classic.roles]
    assert "code_backend" in [role.role for role in classic.roles]
    assert "integration" in [role.role for role in classic.roles]
    assert classic.methodology == "plan-code-test-document"


def test_dev_team_tdd_workflow_records_timings(tmp_path) -> None:
    orchestrator = _orchestrator(tmp_path)
    item = WorkItem(
        objective="Ajouter un endpoint de sante enrichi",
        use_case_id="dev-team-benchmark",
        success_criteria=["Les tests passent", "La documentation est a jour"],
    )

    result = orchestrator.run_dev_team_workflow(item, "team-tdd")

    assert result.team_id == "team-tdd"
    assert [output.role for output in result.outputs] == [
        "write_tests",
        "code_backend",
        "code_frontend",
        "integration",
        "run_fix",
        "document",
    ]
    assert result.total_duration_ms is not None
    assert len(result.step_timings) == 6
    assert result.verification_passed is True


def test_dev_team_benchmark_runs_teams_sequentially(tmp_path) -> None:
    orchestrator = _orchestrator(tmp_path)
    item = WorkItem(
        objective="Implementer un validateur de configuration",
        use_case_id="dev-team-benchmark",
    )

    report = orchestrator.run_dev_team_benchmark(item)

    assert report.team_order == list(DEV_TEAM_BENCHMARK_ORDER)
    assert len(report.runs) == 2
    assert report.runs[0].team_id == "team-tdd"
    assert report.runs[1].team_id == "team-classic"
    assert "team-tdd" in report.comparison.duration_ms_by_team
    assert "team-classic" in report.comparison.duration_ms_by_team
    assert report.comparison.fastest_team_id in {"team-tdd", "team-classic"}


def test_write_tests_runner_registered() -> None:
    from core.agent_runtime import run_agent_request
    from core.contracts import AgentExecutionRequest

    request = AgentExecutionRequest(
        role="write_tests",
        work_item=WorkItem(objective="Feature X", use_case_id="dev-team-benchmark"),
        memory={"state": {}, "events": []},
    )

    response = run_agent_request(request)

    assert response.output.role == "write_tests"
    assert "write_tests_output" in response.memory["state"]


def test_api_lists_dev_teams_and_benchmark_endpoint() -> None:
    reloaded = reload_api_app()
    client = TestClient(reloaded.app)

    teams = client.get("/teams")
    assert teams.status_code == 200
    ids = {team["id"] for team in teams.json()}
    assert {"team-tdd", "team-classic"} == ids

    tdd = client.get("/team", params={"team_id": "team-tdd"})
    assert tdd.status_code == 200
    pipeline = tdd.json()["pipeline_step_ids"]
    assert "code_backend" in pipeline
    assert "code_frontend" in pipeline

    benchmark = client.post(
        "/workflows/dev-team-benchmark",
        json={
            "objective": "Comparer TDD vs plan-code-test sur une API CRUD",
            "team_order": ["team-tdd", "team-classic"],
        },
    )
    assert benchmark.status_code == 200
    payload = benchmark.json()
    assert len(payload["runs"]) == 2
    assert payload["comparison"]["success_by_team"]["team-tdd"] is True
