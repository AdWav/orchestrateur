from core.contracts import WorkItem
from core.orchestrator import MultiAgentOrchestrator


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
