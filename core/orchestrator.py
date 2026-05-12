from __future__ import annotations

from core.agent_gateway import AgentGateway, LocalAgentGateway
from core.contracts import (
    Finding,
    RepoAuditReport,
    RepoAuditRequest,
    RepoAuditValidationReport,
    RepoInventory,
    TeamSpecification,
    WorkflowRun,
    WorkItem,
)
from core.memory import SharedMemory
from core.pipeline import PIPELINE_STEP_IDS
from core.roles import ExecutorAgent, PlannerAgent, ResearcherAgent, VerifierAgent
from core.use_cases import USE_CASES


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
            use_case_ids=[use_case.id for use_case in USE_CASES],
            roles=[
                self.planner.descriptor,
                self.researcher.descriptor,
                self.executor.descriptor,
                self.verifier.descriptor,
            ],
            handoff_contracts=[
                "plan -> research: brief, hypotheses, criteres de succes",
                "research -> execute: preuves requises, gaps, contexte exploitable",
                "execute -> verify: livrable final, checklist, risques restants",
            ],
            guardrails=[
                "Une seule iteration par workflow est prevue avec cette orchestration.",
                "Tous les handoffs sont traces dans la memoire partagee.",
                "Le workflow s'arrete si les sorties attendues manquent.",
            ],
        )

    def _run_linear_workflow(self, item: WorkItem) -> WorkflowRun:
        memory = SharedMemory()
        memory.remember("request", item.model_dump(), "system")

        outputs = []
        memory_snapshot = memory.snapshot()
        for role in PIPELINE_STEP_IDS:
            output, memory_snapshot = self.gateway.run_agent(role, item, memory_snapshot)
            outputs.append(output)
        verification_passed = bool(outputs[-1].approved)
        return WorkflowRun(
            request=item,
            outputs=outputs,
            memory=memory_snapshot,
            verification_passed=verification_passed,
        )

    def run_specification_workflow(self, item: WorkItem) -> WorkflowRun:
        return self._run_linear_workflow(item)

    def run_repo_audit_workflow(self, request: RepoAuditRequest) -> RepoAuditReport:
        workflow = self._run_linear_workflow(request.to_work_item())
        researcher_artifacts = workflow.outputs[1].artifacts if len(workflow.outputs) > 1 else {}
        executor_artifacts = workflow.outputs[2].artifacts if len(workflow.outputs) > 2 else {}
        verifier_artifacts = workflow.outputs[3].artifacts if len(workflow.outputs) > 3 else {}

        inventory_payload = researcher_artifacts.get("repo_inventory")
        findings_payload = executor_artifacts.get("findings", [])
        validation_payload = verifier_artifacts.get("validation_report")

        inventory = RepoInventory.model_validate(inventory_payload) if inventory_payload else None
        findings = [
            Finding.model_validate(finding)
            for finding in findings_payload
            if isinstance(finding, dict)
        ]
        validation_report = (
            RepoAuditValidationReport.model_validate(validation_payload)
            if isinstance(validation_payload, dict)
            else None
        )
        return RepoAuditReport(
            request=request,
            inventory=inventory,
            findings=findings,
            outputs=workflow.outputs,
            validation_report=validation_report,
            memory=workflow.memory,
            verification_passed=workflow.verification_passed,
        )
