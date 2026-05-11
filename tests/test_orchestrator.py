from core.contracts import AuditScope, RepoAuditRequest, RepoTarget, WorkItem
from core.orchestrator import MultiAgentOrchestrator


def _create_repo_fixture(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nArchitecture overview.\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text("services:\n  api:\n    image: demo\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_TOKEN=\n", encoding="utf-8")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text("System architecture notes.\n", encoding="utf-8")


def test_team_specification_exposes_four_specialists() -> None:
    orchestrator = MultiAgentOrchestrator()

    team = orchestrator.team_specification()

    assert team.name == "Specification Team"
    assert [role.role for role in team.roles] == [
        "Planner",
        "Researcher",
        "Executor",
        "Verifier",
    ]
    assert "local-repo-audit" in team.use_case_ids


def test_specification_workflow_runs_end_to_end() -> None:
    orchestrator = MultiAgentOrchestrator()
    item = WorkItem(
        objective="Produire un runbook pour benchmarker trois modeles locaux",
        constraints=["Rester en local", "Conserver une trace des etapes"],
        success_criteria=[
            "Le livrable doit etre actionnable.",
            "Les handoffs doivent etre explicites.",
        ],
        use_case_id="local-model-benchmark",
    )

    result = orchestrator.run_specification_workflow(item)

    assert result.verification_passed is True
    assert [output.role for output in result.outputs] == [
        "Planner",
        "Researcher",
        "Executor",
        "Verifier",
    ]
    assert "planner_output" in result.memory["state"]
    assert "verifier_output" in result.memory["state"]


def test_repo_audit_workflow_runs_end_to_end(tmp_path) -> None:
    _create_repo_fixture(tmp_path)
    orchestrator = MultiAgentOrchestrator()
    request = RepoAuditRequest(
        objective="Auditer le depot local pour confirmer sa structure et sa documentation",
        repo_target=RepoTarget(root_path=str(tmp_path)),
        audit_scope=AuditScope(
            analysis_axes=["architecture", "docs", "dependencies", "security"],
        ),
    )

    result = orchestrator.run_repo_audit_workflow(request)

    assert result.verification_passed is True
    assert result.inventory is not None
    assert "README.md" in result.inventory.important_files
    assert result.validation_report is not None
    assert "docs" in result.validation_report.covered_axes
    assert [output.role for output in result.outputs] == [
        "Planner",
        "Researcher",
        "Executor",
        "Verifier",
    ]
