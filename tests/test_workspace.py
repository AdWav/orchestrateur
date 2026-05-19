from __future__ import annotations

from pathlib import Path

import pytest

from core.contracts import WorkItem
from core.orchestrator import MultiAgentOrchestrator
from core.workspace import build_runner_exec_command, materialize_team_workspace
from core.workspace_templates import detect_scaffold_kind, scaffold_files
from tests.conftest import reload_api_app
from tests.test_dev_teams import _orchestrator


def test_detect_fizzbuzz_scaffold() -> None:
    assert detect_scaffold_kind("Implementer FizzBuzz 1-100") == "fizzbuzz"
    assert detect_scaffold_kind("API CRUD") == "generic_python"


def test_materialize_fizzbuzz_runs_pytest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    team_dir = tmp_path / "run-a" / "team-tdd"
    from core.catalog_bootstrap import ensure_dev_team_catalog
    from core.contracts import WorkflowRun

    orchestrator = _orchestrator(tmp_path / "catalog")
    item = WorkItem(
        objective="Implementer FizzBuzz de 1 a 100",
        use_case_id="dev-team-benchmark",
    )
    run = orchestrator.run_dev_team_workflow(item, "team-tdd")
    info = materialize_team_workspace(team_dir, run, execute_tests=True)

    assert (team_dir / "src" / "fizzbuzz.py").is_file()
    assert (team_dir / "tests" / "test_fizzbuzz.py").is_file()
    assert info.tests_passed is True
    assert "test_fizzbuzz.py" in "\n".join(info.files)


def test_benchmark_creates_workspace_per_team(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "ws"))
    orchestrator = _orchestrator(tmp_path / "catalog")
    report = orchestrator.run_dev_team_benchmark(
        WorkItem(objective="FizzBuzz", use_case_id="dev-team-benchmark"),
        materialize_workspace=True,
    )

    assert report.workspace_run_id
    assert report.workspace_root
    for run in report.runs:
        assert run.workspace is not None
        assert run.team_id
        assert Path(run.workspace.path).is_dir()
        assert run.workspace.tests_passed is True


def test_runner_exec_command_in_compose_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ORCHESTRATOR_MODE", "compose")
    team_dir = tmp_path / "20260101-fizzbuzz" / "team-tdd"
    team_dir.mkdir(parents=True)
    command = build_runner_exec_command(team_dir)
    assert command is not None
    assert "workspace-runner" in command
    assert "/workspaces/20260101-fizzbuzz/team-tdd" in command


def test_scaffold_files_non_empty() -> None:
    files = scaffold_files("fizzbuzz", "FizzBuzz")
    assert "src/fizzbuzz.py" in files
    assert len(files["src/fizzbuzz.py"]) > 50


def test_api_benchmark_returns_workspace_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "ws"))
    reloaded = reload_api_app()
    client = TestClient(reloaded.app)
    response = client.post(
        "/workflows/dev-team-benchmark",
        json={
            "objective": "FizzBuzz 1..100",
            "team_order": ["team-tdd"],
            "materialize_workspace": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("workspace_run_id")
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["workspace"]["path"]
