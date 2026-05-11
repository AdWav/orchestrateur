from __future__ import annotations

from core.agent_gateway import AgentGateway, LocalAgentGateway
from core.contracts import TeamSpecification, WorkflowRun, WorkItem
from core.memory import SharedMemory
from core.roles import ExecutorAgent, PlannerAgent, ResearcherAgent, VerifierAgent
from core.use_cases import V1_USE_CASES


class MultiAgentOrchestrator:
    def __init__(self, gateway: AgentGateway | None = None) -> None:
        self.gateway = gateway or LocalAgentGateway()
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.executor = ExecutorAgent()
        self.verifier = VerifierAgent()

    def team_specification(self) -> TeamSpecification:
        return TeamSpecification(
            name="Specification Team",
            purpose=(
                "Transformer une demande utilisateur en livrable operationnel, "
                "avec recherche, execution et verification."
            ),
            use_case_ids=[use_case.id for use_case in V1_USE_CASES],
            roles=[
                self.planner.descriptor,
                self.researcher.descriptor,
                self.executor.descriptor,
                self.verifier.descriptor,
            ],
            handoff_contracts=[
                "Planner -> Researcher: brief, hypotheses, criteres de succes",
                "Researcher -> Executor: preuves requises, gaps, contexte exploitable",
                "Executor -> Verifier: livrable final, checklist, risques restants",
            ],
            guardrails=[
                "Une seule iteration par workflow dans cette V1.",
                "Tous les handoffs sont traces dans la memoire partagee.",
                "Le workflow s'arrete si les sorties attendues manquent.",
            ],
        )

    def run_specification_workflow(self, item: WorkItem) -> WorkflowRun:
        memory = SharedMemory()
        memory.remember("request", item.model_dump(), "system")

        outputs = []
        memory_snapshot = memory.snapshot()
        for role in ("Planner", "Researcher", "Executor", "Verifier"):
            output, memory_snapshot = self.gateway.run_agent(role, item, memory_snapshot)
            outputs.append(output)
        verification_passed = bool(outputs[-1].approved)
        return WorkflowRun(
            request=item,
            outputs=outputs,
            memory=memory_snapshot,
            verification_passed=verification_passed,
        )
