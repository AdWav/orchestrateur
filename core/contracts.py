from __future__ import annotations

from typing import Any

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
