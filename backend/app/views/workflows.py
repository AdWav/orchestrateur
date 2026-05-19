from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import get_container
from app.models.api_schemas import (
    CatalogWorkflowRunRequest,
    DevTeamBenchmarkWorkflowRequest,
    RepoAuditWorkflowRequest,
    SpecificationWorkflowRequest,
)
from core.contracts import DevTeamBenchmarkReport, RepoAuditReport, WorkflowRun

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/specification", response_model=WorkflowRun)
def run_specification_workflow(request: SpecificationWorkflowRequest) -> WorkflowRun:
    return get_container().workflow_controller.run_specification(request)


@router.post("/repo-audit", response_model=RepoAuditReport)
def run_repo_audit_workflow(request: RepoAuditWorkflowRequest) -> RepoAuditReport:
    return get_container().workflow_controller.run_repo_audit(request)


@router.post("/catalog/{workflow_id}", response_model=WorkflowRun)
def run_catalog_workflow(workflow_id: str, request: CatalogWorkflowRunRequest) -> WorkflowRun:
    return get_container().workflow_controller.run_catalog_workflow(workflow_id, request)


@router.post("/dev-team-benchmark", response_model=DevTeamBenchmarkReport)
def run_dev_team_benchmark_workflow(
    request: DevTeamBenchmarkWorkflowRequest,
) -> DevTeamBenchmarkReport:
    return get_container().workflow_controller.run_dev_team_benchmark(request)
