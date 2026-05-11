from __future__ import annotations

from core.contracts import AgentExecutionRequest, AgentExecutionResponse
from core.memory import SharedMemory
from core.model_client import DryRunModelClient, ModelClient
from core.roles import ExecutorAgent, PlannerAgent, ResearcherAgent, SpecialistAgent, VerifierAgent


ROLE_CLASS_MAP: dict[str, type[SpecialistAgent]] = {
    "Planner": PlannerAgent,
    "Researcher": ResearcherAgent,
    "Executor": ExecutorAgent,
    "Verifier": VerifierAgent,
}


def run_agent_request(
    request: AgentExecutionRequest,
    model_client: ModelClient | None = None,
) -> AgentExecutionResponse:
    if request.role not in ROLE_CLASS_MAP:
        available_roles = ", ".join(sorted(ROLE_CLASS_MAP))
        raise ValueError(f"Unknown role '{request.role}'. Available roles: {available_roles}")

    memory = SharedMemory.from_snapshot(request.memory)
    agent = ROLE_CLASS_MAP[request.role](model_client or DryRunModelClient())
    output = agent.run(request.work_item, memory)
    return AgentExecutionResponse(output=output, memory=memory.snapshot())
