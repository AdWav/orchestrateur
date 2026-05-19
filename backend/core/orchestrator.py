from __future__ import annotations

import time

from core.agent_gateway import AgentGateway, LocalAgentGateway
from core.catalog_workflow_executor import (
    list_catalog_team_workflow_ids,
    run_catalog_workflow,
    workflow_to_team_specification,
)
from core.contracts import (
    DevTeamBenchmarkReport,
    Finding,
    RepoAuditReport,
    RepoAuditRequest,
    RepoAuditValidationReport,
    RepoInventory,
    StepTiming,
    TeamBenchmarkComparison,
    TeamSpecification,
    WorkflowRun,
    WorkItem,
)
from core.definition_catalog import DefinitionCatalog
from core.dev_teams import DEV_TEAM_BENCHMARK_ORDER
from core.memory import SharedMemory
from core.pipeline import PIPELINE_STEP_IDS

DEFAULT_TEAM_ID = "team-tdd"


class MultiAgentOrchestrator:
    def __init__(
        self,
        gateway: AgentGateway | None = None,
        catalog: DefinitionCatalog | None = None,
    ) -> None:
        self.gateway = gateway or LocalAgentGateway()
        self.catalog = catalog

    def team_specification(self, team_id: str | None = None) -> TeamSpecification:
        resolved = team_id or DEFAULT_TEAM_ID
        if self.catalog is None:
            raise RuntimeError("Catalog required for team specifications.")
        return workflow_to_team_specification(self.catalog, resolved)

    def list_team_specifications(self) -> list[TeamSpecification]:
        if self.catalog is None:
            return []
        return [
            workflow_to_team_specification(self.catalog, workflow_id)
            for workflow_id in list_catalog_team_workflow_ids(self.catalog)
        ]

    def _run_linear_workflow(
        self,
        item: WorkItem,
        *,
        team_id: str | None = None,
        step_ids: tuple[str, ...] | None = None,
    ) -> WorkflowRun:
        steps = step_ids or PIPELINE_STEP_IDS
        memory_state_obj = SharedMemory()
        memory_state_obj.remember("request", item.model_dump(), "system")
        memory_snapshot = memory_state_obj.snapshot()

        outputs = []
        timings: list[StepTiming] = []
        workflow_start = time.perf_counter()

        for step in steps:
            step_start = time.perf_counter()
            output, memory_snapshot = self.gateway.run_agent(step, item, memory_snapshot)
            duration_ms = (time.perf_counter() - step_start) * 1000.0
            timings.append(
                StepTiming(
                    step_id=step,
                    duration_ms=round(duration_ms, 2),
                    approved=output.approved,
                )
            )
            outputs.append(output)

        verification_passed = bool(outputs[-1].approved)
        total_duration_ms = round((time.perf_counter() - workflow_start) * 1000.0, 2)

        return WorkflowRun(
            request=item,
            outputs=outputs,
            memory=memory_snapshot,
            verification_passed=verification_passed,
            team_id=team_id,
            step_timings=timings,
            total_duration_ms=total_duration_ms,
        )

    def run_catalog_workflow(self, workflow_id: str, item: WorkItem) -> WorkflowRun:
        if self.catalog is None:
            raise RuntimeError("Catalog required to run workflow presets.")
        return run_catalog_workflow(self.catalog, self.gateway, workflow_id, item)

    def run_specification_workflow(self, item: WorkItem) -> WorkflowRun:
        return self._run_linear_workflow(item, team_id=None, step_ids=PIPELINE_STEP_IDS)

    def run_dev_team_workflow(self, item: WorkItem, team_id: str) -> WorkflowRun:
        return self.run_catalog_workflow(team_id, item)

    def run_dev_team_benchmark(
        self,
        item: WorkItem,
        *,
        team_order: tuple[str, ...] | None = None,
        materialize_workspace: bool = True,
    ) -> DevTeamBenchmarkReport:
        from core.workspace import (
            create_benchmark_workspace,
            materialize_team_workspace,
        )

        order = team_order or DEV_TEAM_BENCHMARK_ORDER
        runs: list[WorkflowRun] = []
        workspace_run = (
            create_benchmark_workspace(item.objective) if materialize_workspace else None
        )
        for workflow_id in order:
            team_item = item
            if workspace_run is not None:
                team_path = workspace_run.team_dir(workflow_id)
                team_path.mkdir(parents=True, exist_ok=True)
                team_item = item.model_copy(
                    update={
                        "context": {
                            **item.context,
                            "workspace_path": str(team_path),
                        }
                    }
                )
            run = self.run_dev_team_workflow(team_item, workflow_id)
            if workspace_run is not None:
                workspace_info = materialize_team_workspace(
                    workspace_run.team_dir(workflow_id),
                    run,
                )
                run = run.model_copy(update={"workspace": workspace_info})
            runs.append(run)

        duration_by_team = {
            run.team_id: run.total_duration_ms or 0.0
            for run in runs
            if run.team_id is not None
        }
        success_by_team = {
            run.team_id: run.verification_passed
            for run in runs
            if run.team_id is not None
        }
        winners = [tid for tid, ok in success_by_team.items() if ok]
        fastest_team_id: str | None = None
        if duration_by_team:
            fastest_team_id = min(duration_by_team, key=duration_by_team.get)

        notes: list[str] = []
        if len(winners) == 2:
            notes.append("Les deux equipes ont reussi; comparer total_duration_ms et les artefacts.")
        elif len(winners) == 0:
            notes.append("Aucune equipe n'a valide le verdict final.")
        elif len(winners) == 1:
            notes.append(f"Seule {winners[0]} a valide le verdict final.")

        comparison = TeamBenchmarkComparison(
            fastest_team_id=fastest_team_id,
            success_by_team=success_by_team,
            duration_ms_by_team=duration_by_team,
            winner_by_success=winners,
            notes=notes,
        )
        return DevTeamBenchmarkReport(
            request=item,
            team_order=list(order),
            runs=runs,
            comparison=comparison,
            workspace_run_id=workspace_run.run_id if workspace_run else None,
            workspace_root=str(workspace_run.root) if workspace_run else None,
        )

    def run_repo_audit_workflow(self, request: RepoAuditRequest) -> RepoAuditReport:
        workflow = self._run_linear_workflow(
            request.to_work_item(),
            team_id=None,
            step_ids=PIPELINE_STEP_IDS,
        )
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
