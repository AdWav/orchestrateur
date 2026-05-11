from __future__ import annotations

from pydantic import BaseModel, Field

from core.contracts import RepoAnalysisAxis, RepoReadLimits
from serve.local_runtime import HardwareProfile, WorkloadProfile


class HealthResponse(BaseModel):
    status: str
    service: str


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
