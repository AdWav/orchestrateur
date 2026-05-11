from core.agent_runtime import run_agent_request
from core.contracts import AgentExecutionRequest, AuditScope, RepoAuditRequest, RepoTarget, WorkItem


def test_planner_service_request_returns_output_and_memory() -> None:
    request = AgentExecutionRequest(
        role="Planner",
        work_item=WorkItem(
            objective="Structurer un workflow local multi-agent",
            constraints=["Rester en local"],
            success_criteria=["Le handoff doit etre explicite"],
        ),
        memory={"state": {}, "events": []},
    )

    response = run_agent_request(request)

    assert response.output.role == "Planner"
    assert "planner_output" in response.memory["state"]


def test_verifier_rejects_repo_audit_without_proofs_or_coverage(tmp_path) -> None:
    request = RepoAuditRequest(
        objective="Auditer le depot sans ecriture",
        repo_target=RepoTarget(root_path=str(tmp_path)),
        audit_scope=AuditScope(analysis_axes=["docs"]),
    )
    verifier_request = AgentExecutionRequest(
        role="Verifier",
        work_item=request.to_work_item(),
        memory={
            "state": {
                "researcher_output": {
                    "artifacts": {
                        "evidence_refs": [],
                        "coverage_map": {"docs": []},
                    }
                },
                "executor_output": {
                    "artifacts": {
                        "findings": [
                            {
                                "id": "finding-1",
                                "category": "docs",
                                "severity": "medium",
                                "title": "Docs gap",
                                "summary": "Missing proof",
                                "impacted_paths": [],
                                "evidence_refs": [],
                                "recommended_actions": [],
                            }
                        ]
                    }
                },
            },
            "events": [],
        },
    )

    response = run_agent_request(verifier_request)

    validation_report = response.output.artifacts["validation_report"]
    assert response.output.approved is False
    assert "Axe non couvert: docs" in validation_report["missing_requirements"]
    assert validation_report["unsupported_claims"]
