from core.agent_runtime import run_agent_request
from core.contracts import AgentExecutionRequest, WorkItem


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
