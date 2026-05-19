from __future__ import annotations

from core.catalog_runtime import enrich_work_item_prompt
from core.contracts import AgentOutput, WorkItem
from core.memory import SharedMemory
from core.model_client import DryRunModelClient, ModelClient
from core.roles import SpecialistAgent


class CatalogGenericAgent(SpecialistAgent):
    """Runner catalogue sans specialiste code : prompt enrichi par la fiche agent."""

    def __init__(
        self,
        runner_role: str,
        model_client: ModelClient | None = None,
    ) -> None:
        super().__init__(model_client=model_client or DryRunModelClient())
        self._runner_role = runner_role
        from core.contracts import AgentDescriptor

        self.descriptor = AgentDescriptor(
            role=runner_role,
            responsibility="Executer la mission definie dans le catalogue.",
            capabilities=["catalog-driven"],
            allowed_inputs=["objectif", "contexte catalogue"],
            produces=["catalog_output"],
        )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        base_prompt = (
            f"Role: {self._runner_role}\n"
            f"Objective: {item.objective}\n"
            f"Constraints: {', '.join(item.constraints) or 'none'}\n"
            f"Success criteria: {', '.join(item.success_criteria) or 'none'}"
        )
        prompt = enrich_work_item_prompt(base_prompt, memory)
        summary = self.model_client.generate(self._runner_role, prompt).content
        agent_id = memory.read("catalog_agent", {})
        agent_name = agent_id.get("name", self._runner_role) if isinstance(agent_id, dict) else self._runner_role

        output = AgentOutput(
            role=self._runner_role,
            summary=summary,
            artifacts={
                "catalog_agent_id": agent_id.get("id") if isinstance(agent_id, dict) else None,
                "agent_name": agent_name,
                "deliverable": summary[:500],
            },
            next_actions=["Transmettre au runner suivant du workflow."],
            approved=True,
        )
        memory.remember(f"{self._runner_role}_output", output.model_dump(), self._runner_role)
        return output
