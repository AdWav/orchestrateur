from __future__ import annotations

from pydantic import BaseModel, Field

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
