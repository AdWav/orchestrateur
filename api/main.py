from __future__ import annotations

from fastapi import FastAPI

from api.schemas import (
    HealthResponse,
    RepoAuditWorkflowRequest,
    RuntimeRecommendationRequest,
    SpecificationWorkflowRequest,
)
from api.settings import build_role_urls, running_in_compose
from core.agent_gateway import HttpAgentGateway, LocalAgentGateway
from core.contracts import (
    AuditScope,
    RepoAuditReport,
    RepoAuditRequest,
    RepoTarget,
    TeamSpecification,
    UseCaseDefinition,
    WorkflowRun,
    WorkItem,
)
from core.model_client import build_model_client_from_env
from core.orchestrator import MultiAgentOrchestrator
from core.use_cases import V1_USE_CASES
from serve.local_runtime import RuntimeRecommendation, recommend_runtime

app = FastAPI(
    title="Orchestrateur Local Multi-Agents",
    version="0.1.0",
    description="Control plane Python-first pour agents locaux specialises.",
)

gateway = (
    HttpAgentGateway(build_role_urls())
    if running_in_compose()
    else LocalAgentGateway(model_client=build_model_client_from_env())
)
orchestrator = MultiAgentOrchestrator(gateway=gateway)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="orchestrateur-local")


@app.get("/v1/use-cases", response_model=list[UseCaseDefinition])
def list_use_cases() -> list[UseCaseDefinition]:
    return V1_USE_CASES


@app.get("/v1/team", response_model=TeamSpecification)
def team_specification() -> TeamSpecification:
    return orchestrator.team_specification()


@app.post("/v1/runtime/recommendation", response_model=RuntimeRecommendation)
def runtime_recommendation(
    request: RuntimeRecommendationRequest,
) -> RuntimeRecommendation:
    return recommend_runtime(request.hardware, request.workload)


@app.post("/v1/workflows/specification", response_model=WorkflowRun)
def run_specification_workflow(
    request: SpecificationWorkflowRequest,
) -> WorkflowRun:
    work_item = WorkItem(
        objective=request.objective,
        context=request.context,
        constraints=request.constraints,
        success_criteria=request.success_criteria,
        use_case_id=request.use_case_id,
    )
    return orchestrator.run_specification_workflow(work_item)


@app.post("/v1/workflows/repo-audit", response_model=RepoAuditReport)
def run_repo_audit_workflow(
    request: RepoAuditWorkflowRequest,
) -> RepoAuditReport:
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
    return orchestrator.run_repo_audit_workflow(audit_request)
