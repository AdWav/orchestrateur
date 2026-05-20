from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from core.contracts import RepoAnalysisAxis, RepoReadLimits
from core.pipeline import RUNNER_STEP_IDS
from serve.local_runtime import HardwareProfile, WorkloadProfile


class HealthResponse(BaseModel):
    status: str
    service: str


class ServiceStatus(BaseModel):
    key: str
    label: str
    target: str
    port: str | None = None
    active: bool


class ServiceMeshStatusResponse(BaseModel):
    services: list[ServiceStatus]


class OllamaModelsResponse(BaseModel):
    """Liste des noms de modèles visibles depuis Ollama (`ollama list` / `/api/tags`)."""

    models: list[str]


class OllamaRuntimeSettingsUpdate(BaseModel):
    default_model: str = Field(min_length=1, max_length=256)
    runner_models: dict[str, str]

    @field_validator("runner_models")
    @classmethod
    def runners_complete(cls, runners: dict[str, str]) -> dict[str, str]:
        missing = [sid for sid in RUNNER_STEP_IDS if sid not in runners]
        if missing:
            raise ValueError(f"Cles runner manquantes: {sorted(missing)}.")
        extras = sorted(set(runners) - set(RUNNER_STEP_IDS))
        if extras:
            raise ValueError(f"Cles runner inconnues: {extras}.")
        for sid in RUNNER_STEP_IDS:
            candidate = runners.get(sid, "")
            if not isinstance(candidate, str) or not candidate.strip():
                raise ValueError(f"Modele invalide ou vide pour l'etape {sid}.")
        return runners


class OllamaRuntimeSettingsResponse(BaseModel):
    default_model: str
    runner_models: dict[str, str]
    pipeline_steps: list[str]
    settings_persist_path: str | None = None
    ollama_routing_active: bool = False


class ModelWarmUnloadAck(BaseModel):
    model: str
    action: Literal["warm", "unload"]


class SamplingProfile(BaseModel):
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    min_p: float | None = Field(default=None, ge=0.0, le=1.0)
    mirostat: int | None = Field(default=None, ge=0, le=2)
    mirostat_eta: float | None = Field(default=None, ge=0.0)
    mirostat_tau: float | None = Field(default=None, ge=0.0)
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    repeat_penalty: float | None = Field(default=None, ge=0.0)
    repeat_last_n: int | None = Field(default=None, ge=-1)
    logit_bias: dict[str, float] | None = None
    stop: list[str] | None = None
    num_predict: int | None = Field(default=None, ge=1)


class SamplingLiveUpdate(SamplingProfile):
    """Profil live : seul celui-ci est modifiable via l'API (PUT)."""


class SamplingSettingsResponse(BaseModel):
    orchestration: SamplingProfile
    live: SamplingProfile
    settings_persist_path: str | None = None
    ollama_active: bool = False


class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=16_384)


class SamplingPreviewRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=32_768)
    model: str | None = Field(default=None, max_length=256)
    """Historique multi-tours (user/assistant) envoye a Ollama /api/chat avant le prompt courant."""
    history: list[ChatTurn] = Field(default_factory=list, max_length=64)


class SamplingPreviewResponse(BaseModel):
    model: str
    profile: Literal["live"] = "live"
    content: str
    backend: str


class ModelTokenPiece(BaseModel):
    id: int
    text: str


class SamplingTokenizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=128_000)
    model: str | None = Field(default=None, max_length=256)


class SamplingTokenizeResponse(BaseModel):
    model: str
    source: Literal["ollama", "llama_cpp"]
    token_count: int
    tokens: list[ModelTokenPiece]


class SamplingTokenizeCapabilitiesResponse(BaseModel):
    ollama_api: bool
    llama_cpp: bool
    source: Literal["ollama", "llama_cpp", "unavailable"]


class RuntimeRecommendationRequest(BaseModel):
    hardware: HardwareProfile
    workload: WorkloadProfile


class SpecificationWorkflowRequest(BaseModel):
    objective: str
    context: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(
        default_factory=lambda: [
            "Le livrable doit etre actionnable.",
            "Les handoffs doivent etre explicites.",
            "Le resultat doit pouvoir etre verifie.",
        ]
    )
    use_case_id: str = "specification-factory"


class CatalogWorkflowRunRequest(BaseModel):
    objective: str
    context: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    use_case_id: str | None = None


class DevTeamBenchmarkWorkflowRequest(BaseModel):
    objective: str
    context: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(
        default_factory=lambda: [
            "Comparer deux methodologies sans elargir le scope.",
            "Tracer les temps par etape.",
        ]
    )
    success_criteria: list[str] = Field(
        default_factory=lambda: [
            "Chaque equipe produit tests, code, execution et documentation.",
            "Le benchmark expose succes/echec et duree par equipe.",
        ]
    )
    team_order: list[str] = Field(
        default_factory=lambda: ["team-tdd", "team-classic"],
        description="Ordre d'execution des equipes (sequentiel).",
    )
    materialize_workspace: bool = Field(
        default=True,
        description="Ecrire un workspace disque par equipe (code + tests executables).",
    )


class RepoAuditWorkflowRequest(BaseModel):
    objective: str
    repo_path: str = "."
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(
        default_factory=lambda: [
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
        ]
    )
    analysis_axes: list[RepoAnalysisAxis] = Field(
        default_factory=lambda: ["architecture", "tests", "docs", "security", "dependencies"]
    )
    read_limits: RepoReadLimits = Field(default_factory=RepoReadLimits)
    constraints: list[str] = Field(
        default_factory=lambda: ["Ne pas modifier le depot cible.", "Rester strictement en lecture seule."]
    )
    success_criteria: list[str] = Field(
        default_factory=lambda: [
            "Le rapport doit citer des preuves traceables.",
            "Le scope d'analyse doit etre explicite.",
            "Le verdict final doit rester verifiable.",
        ]
    )


class BuilderBrickSummaryResponse(BaseModel):
    id: int
    slug: str
    label: str
    description: str | None = None
    status: str
    source: str
    type_code: str
    domain_code: str | None = None


class BuilderBrickDetailResponse(BuilderBrickSummaryResponse):
    metadata: dict[str, object] = Field(default_factory=dict)


class BuilderCatalogAgentResponse(BaseModel):
    id: str
    domain_id: int | None = None
    published_version: str | None = None


class BuilderCatalogAgentVersionResponse(BaseModel):
    id: int
    agent_id: str
    version: str
    status: str
    runner_role: str | None = None
    published_at: str | None = None
    created_at: str | None = None


class BuilderPendingBrickResponse(BaseModel):
    id: int
    target_brick_id: int | None = None
    field_path: str
    proposed_value: object
    status: str
    proposed_by: str
    session_id: str | None = None
    created_at: str | None = None


class BuilderAuditEventResponse(BaseModel):
    id: int
    session_id: str | None = None
    entity_type: str
    entity_id: str
    entity_version: str | None = None
    action: str
    actor_type: str
    actor_id: str
    created_at: str | None = None


class BuilderCreateBrickRequest(BaseModel):
    type_code: str
    label: str
    domain_code: str | None = None
    description: str | None = None
    slug: str | None = None


class BuilderPendingBrickCreateRequest(BaseModel):
    field_path: str
    proposed_value: object
    target_brick_id: int | None = None
    type_code: str | None = None
    session_id: str | None = None
    proposed_by: str = "llm"


class BuilderCompositionItemRequest(BaseModel):
    slot: str
    brick_id: int
    sort_order: int = 0


class BuilderAgentDraftRequest(BaseModel):
    agent_id: str
    name: str
    mission: str
    composition: list[BuilderCompositionItemRequest]
    domain_code: str | None = "dev"
    runner_role: str | None = None
    business_role: str | None = None


class BuilderWorkflowStepDraftRequest(BaseModel):
    id: str
    name: str
    agent_definition_id: str
    objective: str
    depends_on: list[str] = Field(default_factory=list)
    runner_role: str | None = None


class BuilderWorkflowDraftRequest(BaseModel):
    workflow_id: str
    name: str
    goal: str
    steps: list[BuilderWorkflowStepDraftRequest]
    context: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    domain_code: str | None = "dev"


class BuilderCustomAgentDraftRequest(BaseModel):
    slug: str
    name: str
    mission: str
    composition: list[BuilderCompositionItemRequest]
    owner_user_id: str
    workspace_id: str | None = None
    runner_role: str | None = None
    business_role: str | None = None


class BuilderDraftResponse(BaseModel):
    agent_id: str | None = None
    workflow_id: str | None = None
    custom_agent_id: str | None = None
    version_id: int
    version: str
    status: str


class BuilderPublishResponse(BaseModel):
    agent_id: str | None = None
    workflow_id: str | None = None
    custom_agent_id: str | None = None
    custom_workflow_id: str | None = None
    version_id: int
    version: str
    status: str
    runtime_agent_id: str | None = None
    runtime_workflow_id: str | None = None


class BuilderCatalogWorkflowResponse(BaseModel):
    id: str
    domain_id: int | None = None
    published_version: str | None = None


class BuilderCustomAgentSummaryResponse(BaseModel):
    id: str
    slug: str
    workspace_id: str | None = None
    owner_user_id: str
    version_id: int | None = None
    version: str | None = None
    status: str | None = None
    created_at: str | None = None


class BuilderPendingDecisionResponse(BaseModel):
    id: int
    status: str
    merged_brick_id: int | None = None
    draft_version_id: int | None = None


class BuilderPendingAgentResponse(BaseModel):
    id: int
    draft_version_id: int
    field_path: str
    proposed_value: object
    status: str
    proposed_by: str
    session_id: str | None = None
    created_at: str | None = None


class BuilderPendingAgentCreateRequest(BaseModel):
    draft_version_id: int
    field_path: str
    proposed_value: object
    session_id: str | None = None
    proposed_by: str = "llm"


class BuilderCustomWorkflowDraftRequest(BaseModel):
    slug: str
    name: str
    goal: str
    steps: list[BuilderWorkflowStepDraftRequest]
    owner_user_id: str
    workspace_id: str | None = None
    context: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)


class BuilderCustomWorkflowSummaryResponse(BaseModel):
    id: str
    slug: str
    workspace_id: str | None = None
    owner_user_id: str
    version_id: int | None = None
    version: str | None = None
    status: str | None = None
    created_at: str | None = None


class BuilderPromotionSubmitRequest(BaseModel):
    requester_id: str
    source_kind: str
    source_id: str
    target_kind: str
    proposed_payload: dict[str, object] = Field(default_factory=dict)
    target_id: str | None = None


class BuilderPromotionResponse(BaseModel):
    id: int
    requester_id: str | None = None
    source_kind: str | None = None
    source_id: str | None = None
    target_kind: str | None = None
    target_id: str | None = None
    proposed_payload: dict[str, object] | None = None
    status: str
    catalog_agent_id: str | None = None
    catalog_version_id: int | None = None
    reviewer_id: str | None = None
    created_at: str | None = None
    resolved_at: str | None = None


class BuilderPromotionReviewRequest(BaseModel):
    review_notes: str | None = None


class BuilderSessionCreateRequest(BaseModel):
    kind: str
    actor_type: str
    actor_id: str
    goal_prompt: str | None = None
    session_id: str | None = None


class BuilderSessionResponse(BaseModel):
    id: str
    kind: str
    actor_type: str
    actor_id: str
    goal_prompt: str | None = None
    started_at: str | None = None
    ended_at: str | None = None


class BuilderSessionDetailResponse(BaseModel):
    session: BuilderSessionResponse
    inputs: list[dict[str, object]] = Field(default_factory=list)
    outputs: list[dict[str, object]] = Field(default_factory=list)
    audit_events: list[BuilderAuditEventResponse] = Field(default_factory=list)
