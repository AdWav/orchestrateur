from __future__ import annotations

from core.contracts import AgentExecutionRequest, AgentExecutionResponse
from core.dev_teams import ALL_DEV_RUNNER_STEP_IDS
from core.memory import SharedMemory
from core.model_client import DryRunModelClient, ModelClient
from core.pipeline import LEGACY_PIPELINE_STEP_IDS
from core.roles import ExecutorAgent, PlannerAgent, ResearcherAgent, SpecialistAgent, VerifierAgent
from core.catalog_generic_agent import CatalogGenericAgent
from core.roles_dev import dev_agent_for_step


LEGACY_STEP_RUNNER_CLASS_MAP: dict[str, type[SpecialistAgent]] = {
    "plan": PlannerAgent,
    "research": ResearcherAgent,
    "execute": ExecutorAgent,
    "verify": VerifierAgent,
}

STEP_RUNNER_CLASS_MAP: dict[str, type[SpecialistAgent]] = dict(LEGACY_STEP_RUNNER_CLASS_MAP)


def _instantiate_runner(step_id: str, model_client: ModelClient | None) -> SpecialistAgent:
    client = model_client or DryRunModelClient()
    if step_id in LEGACY_STEP_RUNNER_CLASS_MAP:
        return LEGACY_STEP_RUNNER_CLASS_MAP[step_id](model_client=client)
    if step_id in ALL_DEV_RUNNER_STEP_IDS:
        return dev_agent_for_step(step_id, model_client=model_client)
    if step_id == "generic":
        return CatalogGenericAgent("generic", model_client=client)
    available = ", ".join(sorted({*LEGACY_STEP_RUNNER_CLASS_MAP, *ALL_DEV_RUNNER_STEP_IDS, "generic"}))
    raise ValueError(f"Unknown runner step '{step_id}'. Available runners: {available}")


def run_agent_request(
    request: AgentExecutionRequest,
    model_client: ModelClient | None = None,
) -> AgentExecutionResponse:
    memory = SharedMemory.from_snapshot(request.memory)
    agent = _instantiate_runner(request.role, model_client)
    output = agent.run(request.work_item, memory)
    return AgentExecutionResponse(output=output, memory=memory.snapshot())
