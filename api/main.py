from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from api.context import attach_runtime_ollama
from api.ollama_runtime_router import router as ollama_runtime_router
from api.schemas import (
    HealthResponse,
    RepoAuditWorkflowRequest,
    RuntimeRecommendationRequest,
    ServiceMeshStatusResponse,
    SpecificationWorkflowRequest,
)
from api.service_status import collect_service_status
from api.settings import build_role_urls, running_in_compose, ui_allowed_origins
from core.agent_gateway import HttpAgentGateway, LocalAgentGateway
from core.contracts import (
    AgentDefinition,
    AuditScope,
    RepoAuditReport,
    RepoAuditRequest,
    RepoTarget,
    TeamSpecification,
    UseCaseDefinition,
    WorkflowDefinition,
    WorkflowRun,
    WorkItem,
)
from core.definition_catalog import FileDefinitionCatalog
from core.model_client import build_model_client_from_env
from core.orchestrator import MultiAgentOrchestrator
from core.runtime_ollama_settings import RuntimeOllamaSettings
from core.use_cases import USE_CASES
from serve.local_runtime import RuntimeRecommendation, recommend_runtime

_runtime_settings = RuntimeOllamaSettings.bootstrap_from_environment()
attach_runtime_ollama(_runtime_settings)

app = FastAPI(
    title="Orchestrateur Local Multi-Agents",
    version="0.1.0",
    description="Control plane Python-first pour agents locaux specialises.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ui_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ollama_runtime_router)

gateway = (
    HttpAgentGateway(build_role_urls())
    if running_in_compose()
    else LocalAgentGateway(model_client=build_model_client_from_env(_runtime_settings))
)
orchestrator = MultiAgentOrchestrator(gateway=gateway)
catalog = FileDefinitionCatalog()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="orchestrateur-local")


@app.get("/services/status", response_model=ServiceMeshStatusResponse)
def service_status() -> ServiceMeshStatusResponse:
    return collect_service_status()


@app.get("/use-cases", response_model=list[UseCaseDefinition])
def list_use_cases() -> list[UseCaseDefinition]:
    return USE_CASES


@app.get("/definitions/agents", response_model=list[AgentDefinition])
def list_agent_definitions() -> list[AgentDefinition]:
    return catalog.list_agents()


@app.post(
    "/definitions/agents",
    response_model=AgentDefinition,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_definition(definition: AgentDefinition) -> AgentDefinition:
    try:
        return catalog.save_agent(definition)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/definitions/workflows", response_model=list[WorkflowDefinition])
def list_workflow_definitions() -> list[WorkflowDefinition]:
    return catalog.list_workflows()


@app.post(
    "/definitions/workflows",
    response_model=WorkflowDefinition,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_definition(definition: WorkflowDefinition) -> WorkflowDefinition:
    try:
        return catalog.save_workflow(definition)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/team", response_model=TeamSpecification)
def team_specification() -> TeamSpecification:
    return orchestrator.team_specification()


@app.post("/runtime/recommendation", response_model=RuntimeRecommendation)
def runtime_recommendation(request: RuntimeRecommendationRequest) -> RuntimeRecommendation:
    return recommend_runtime(request.hardware, request.workload)


@app.post("/workflows/specification", response_model=WorkflowRun)
def run_specification_workflow(request: SpecificationWorkflowRequest) -> WorkflowRun:
    work_item = WorkItem(
        objective=request.objective,
        context=request.context,
        constraints=request.constraints,
        success_criteria=request.success_criteria,
        use_case_id=request.use_case_id,
    )
    return orchestrator.run_specification_workflow(work_item)


@app.post("/workflows/repo-audit", response_model=RepoAuditReport)
def run_repo_audit_workflow(request: RepoAuditWorkflowRequest) -> RepoAuditReport:
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
