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


class SamplingPreviewRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=32_768)
    model: str | None = Field(default=None, max_length=256)


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
