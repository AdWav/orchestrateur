from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ToolPolicy(BaseModel):
    allowed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)


class Guardrails(BaseModel):
    require_verification: bool = True
    must_log_handoffs: bool = True
    max_iterations: int = 1
    stop_conditions: list[str] = Field(default_factory=list)


class WorkItem(BaseModel):
    objective: str
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    expected_output: str = "execution-brief"
    use_case_id: str | None = None
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    guardrails: Guardrails = Field(default_factory=Guardrails)


RepoAnalysisAxis = Literal["architecture", "tests", "docs", "security", "dependencies"]
FindingSeverity = Literal["low", "medium", "high"]
FindingConfidence = Literal["low", "medium", "high"]

_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{1,62})$")


def _validated_identifier(raw: str, field_name: str) -> str:
    value = raw.strip().lower()
    if not _IDENTIFIER_PATTERN.match(value):
        raise ValueError(
            f"{field_name} must match '{_IDENTIFIER_PATTERN.pattern}' and stay URL-friendly."
        )
    return value


class RepoReadLimits(BaseModel):
    max_files: int = 40
    max_bytes_per_file: int = 12000
    max_matches: int = 40


class RepoTarget(BaseModel):
    root_path: str = "."


class AuditScope(BaseModel):
    analysis_axes: list[RepoAnalysisAxis] = Field(
        default_factory=lambda: ["architecture", "tests", "docs", "security", "dependencies"]
    )
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
    read_limits: RepoReadLimits = Field(default_factory=RepoReadLimits)


class EvidenceRef(BaseModel):
    path: str
    kind: str
    reason: str
    excerpt: str = ""
    line_start: int | None = None
    line_end: int | None = None


class RepoInventory(BaseModel):
    root_path: str
    total_files_scanned: int
    top_level_entries: list[str] = Field(default_factory=list)
    detected_languages: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    scanned_paths: list[str] = Field(default_factory=list)
    truncated: bool = False


class Finding(BaseModel):
    id: str
    category: str
    severity: FindingSeverity
    title: str
    summary: str
    impacted_paths: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    confidence: FindingConfidence = "medium"


class RepoAuditValidationReport(BaseModel):
    approved: bool
    covered_axes: list[RepoAnalysisAxis] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    policy_compliance: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    evidence_count: int = 0


class RepoAuditRequest(BaseModel):
    objective: str
    repo_target: RepoTarget = Field(default_factory=RepoTarget)
    audit_scope: AuditScope = Field(default_factory=AuditScope)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(
        default_factory=lambda: [
            "Le rapport doit citer des preuves traceables.",
            "Le scope d'analyse doit etre explicite.",
            "Aucune action d'ecriture ne doit etre realisee.",
        ]
    )
    use_case_id: str = "local-repo-audit"
    expected_output: str = "repo-audit-report"
    tool_policy: ToolPolicy = Field(
        default_factory=lambda: ToolPolicy(
            allowed_tools=[
                "repo.list_tree",
                "repo.read_text_file",
                "repo.search_code",
            ],
            blocked_tools=[
                "repo.write",
                "repo.delete",
                "shell.exec",
            ],
        )
    )
    guardrails: Guardrails = Field(
        default_factory=lambda: Guardrails(
            require_verification=True,
            must_log_handoffs=True,
            max_iterations=1,
            stop_conditions=[
                "Ne pas modifier le depot cible.",
                "Ne pas emettre de conclusion sans preuve.",
            ],
        )
    )

    def to_work_item(self) -> WorkItem:
        return WorkItem(
            objective=self.objective,
            context={"repo_audit": self.model_dump(mode="python")},
            constraints=self.constraints,
            success_criteria=self.success_criteria,
            expected_output=self.expected_output,
            use_case_id=self.use_case_id,
            tool_policy=self.tool_policy,
            guardrails=self.guardrails,
        )


class AgentDescriptor(BaseModel):
    role: str
    responsibility: str
    capabilities: list[str]
    allowed_inputs: list[str]
    produces: list[str]


class AgentOutput(BaseModel):
    role: str
    summary: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    next_actions: list[str] = Field(default_factory=list)
    approved: bool | None = None


class TeamSpecification(BaseModel):
    id: str = "team-tdd"
    name: str
    purpose: str
    methodology: str | None = None
    use_case_ids: list[str]
    roles: list[AgentDescriptor]
    pipeline_step_ids: list[str] = Field(default_factory=list)
    handoff_contracts: list[str]
    guardrails: list[str]


class StepTiming(BaseModel):
    step_id: str
    duration_ms: float
    approved: bool | None = None


class WorkspaceInfo(BaseModel):
    path: str
    files: list[str] = Field(default_factory=list)
    test_command: str = "pytest -q"
    runner_exec_command: str | None = None
    tests_passed: bool | None = None
    test_output: str | None = None


class WorkflowRun(BaseModel):
    request: WorkItem
    outputs: list[AgentOutput]
    memory: dict[str, Any]
    verification_passed: bool
    team_id: str | None = None
    step_timings: list[StepTiming] = Field(default_factory=list)
    total_duration_ms: float | None = None
    workspace: WorkspaceInfo | None = None


class TeamBenchmarkComparison(BaseModel):
    fastest_team_id: str | None = None
    success_by_team: dict[str, bool]
    duration_ms_by_team: dict[str, float]
    winner_by_success: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DevTeamBenchmarkReport(BaseModel):
    request: WorkItem
    team_order: list[str]
    runs: list[WorkflowRun]
    comparison: TeamBenchmarkComparison
    workspace_run_id: str | None = None
    workspace_root: str | None = None


class RepoAuditReport(BaseModel):
    request: RepoAuditRequest
    inventory: RepoInventory | None = None
    findings: list[Finding] = Field(default_factory=list)
    outputs: list[AgentOutput] = Field(default_factory=list)
    validation_report: RepoAuditValidationReport | None = None
    memory: dict[str, Any] = Field(default_factory=dict)
    verification_passed: bool


class UseCaseDefinition(BaseModel):
    id: str
    title: str
    description: str
    primary_outcome: str
    inputs: list[str]
    deliverables: list[str]


class AgentExecutionRequest(BaseModel):
    role: str
    work_item: WorkItem
    memory: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionResponse(BaseModel):
    output: AgentOutput
    memory: dict[str, Any] = Field(default_factory=dict)


class AgentDefinition(BaseModel):
    """Fiche agent immuable du catalogue : identite metier + runner technique pour l'execution."""

    id: str
    name: str
    business_role: str
    mission: str
    runner_role: str = Field(
        default="",
        description="Identifiant du runner (ex. write_tests, code). Vide = agent generique catalogue.",
    )
    capabilities: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _validated_identifier(value, "AgentDefinition.id")

    @field_validator("name", "business_role", "mission")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Agent definition text fields cannot be empty.")
        return cleaned


class WorkflowStepDefinition(BaseModel):
    id: str
    name: str
    agent_definition_id: str
    objective: str
    runner_role: str | None = Field(
        default=None,
        description="Surcharge ponctuelle du runner de l'agent pour cette etape du workflow.",
    )
    expected_deliverables: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _validated_identifier(value, "WorkflowStepDefinition.id")

    @field_validator("agent_definition_id")
    @classmethod
    def validate_agent_definition_id(cls, value: str) -> str:
        return _validated_identifier(value, "WorkflowStepDefinition.agent_definition_id")

    @field_validator("name", "objective")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Workflow step text fields cannot be empty.")
        return cleaned


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    goal: str
    context: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    steps: list[WorkflowStepDefinition] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _validated_identifier(value, "WorkflowDefinition.id")

    @field_validator("name", "goal")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Workflow definition text fields cannot be empty.")
        return cleaned

    @model_validator(mode="after")
    def validate_steps(self) -> "WorkflowDefinition":
        if not self.steps:
            raise ValueError("WorkflowDefinition.steps must contain at least one step.")

        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("WorkflowDefinition.steps contains duplicate step ids.")

        known_steps = set(step_ids)
        for step in self.steps:
            unknown_dependencies = [dependency for dependency in step.depends_on if dependency not in known_steps]
            if unknown_dependencies:
                unknown = ", ".join(sorted(unknown_dependencies))
                raise ValueError(
                    f"Workflow step '{step.id}' depends on unknown steps: {unknown}."
                )
        return self


