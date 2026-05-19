from __future__ import annotations

from app.models.api_schemas import (
    CatalogWorkflowRunRequest,
    DevTeamBenchmarkWorkflowRequest,
    RepoAuditWorkflowRequest,
    SpecificationWorkflowRequest,
)
from core.contracts import (
    AuditScope,
    DevTeamBenchmarkReport,
    RepoAuditReport,
    RepoAuditRequest,
    RepoTarget,
    WorkflowRun,
    WorkItem,
)
from core.orchestrator import MultiAgentOrchestrator


class WorkflowController:
    def __init__(self, orchestrator: MultiAgentOrchestrator) -> None:
        self._orchestrator = orchestrator

    def run_specification(self, request: SpecificationWorkflowRequest) -> WorkflowRun:
        work_item = WorkItem(
            objective=request.objective,
            context=request.context,
            constraints=request.constraints,
            success_criteria=request.success_criteria,
            use_case_id=request.use_case_id,
        )
        return self._orchestrator.run_specification_workflow(work_item)

    def run_repo_audit(self, request: RepoAuditWorkflowRequest) -> RepoAuditReport:
        audit_request = RepoAuditRequest(
            objective=request.objective,
            repo_target=RepoTarget(root_path=request.repo_path),
            audit_scope=AuditScope(
                analysis_axes=request.analysis_axes,
                include_paths=request.include_paths,
                exclude_paths=request.exclude_paths,
                read_limits=request.read_limits,
            ),
            constraints=request.constraints,
            success_criteria=request.success_criteria,
        )
        return self._orchestrator.run_repo_audit_workflow(audit_request)

    def run_catalog_workflow(
        self,
        workflow_id: str,
        request: CatalogWorkflowRunRequest,
    ) -> WorkflowRun:
        work_item = WorkItem(
            objective=request.objective,
            context=request.context,
            constraints=request.constraints,
            success_criteria=request.success_criteria,
            use_case_id=request.use_case_id,
        )
        return self._orchestrator.run_catalog_workflow(workflow_id, work_item)

    def run_dev_team_benchmark(self, request: DevTeamBenchmarkWorkflowRequest) -> DevTeamBenchmarkReport:
        work_item = WorkItem(
            objective=request.objective,
            context=request.context,
            constraints=request.constraints,
            success_criteria=request.success_criteria,
            use_case_id="dev-team-benchmark",
            expected_output="dev-team-benchmark-report",
        )
        return self._orchestrator.run_dev_team_benchmark(
            work_item,
            team_order=tuple(request.team_order),
            materialize_workspace=request.materialize_workspace,
        )
