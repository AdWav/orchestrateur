from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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
    name: str
    purpose: str
    use_case_ids: list[str]
    roles: list[AgentDescriptor]
    handoff_contracts: list[str]
    guardrails: list[str]


class WorkflowRun(BaseModel):
    request: WorkItem
    outputs: list[AgentOutput]
    memory: dict[str, Any]
    verification_passed: bool


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
