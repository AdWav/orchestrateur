from __future__ import annotations

from typing import Any

from core.contracts import AgentDefinition, WorkflowDefinition, WorkflowStepDefinition
from core.memory import SharedMemory
from core.pipeline import LEGACY_PIPELINE_STEP_IDS
from core.dev_teams import DEV_PIPELINE_STEP_IDS

KNOWN_RUNNER_ROLES = frozenset(
    {
        *LEGACY_PIPELINE_STEP_IDS,
        *DEV_PIPELINE_STEP_IDS,
        "generic",
    }
)


def resolve_runner_role(agent: AgentDefinition, step: WorkflowStepDefinition) -> str:
    override = (step.runner_role or "").strip()
    if override:
        return override
    role = (agent.runner_role or "").strip()
    if role:
        return role
    return "generic"


def enrich_work_item_prompt(item_prompt: str, memory: SharedMemory) -> str:
    agent_payload = memory.read("catalog_agent", {})
    step_payload = memory.read("catalog_step", {})
    if not isinstance(agent_payload, dict) or not agent_payload:
        return item_prompt

    agent_name = agent_payload.get("name", agent_payload.get("id", "agent"))
    business_role = agent_payload.get("business_role", "")
    mission = agent_payload.get("mission", "")
    guardrails = agent_payload.get("guardrails", [])
    capabilities = agent_payload.get("capabilities", [])
    step_objective = ""
    if isinstance(step_payload, dict):
        step_objective = str(step_payload.get("objective", "")).strip()

    lines = [
        item_prompt,
        "",
        f"Catalog agent: {agent_name} ({business_role})",
        f"Mission: {mission}",
    ]
    if step_objective:
        lines.append(f"Step objective: {step_objective}")
    if capabilities:
        lines.append(f"Capabilities: {', '.join(str(c) for c in capabilities)}")
    if guardrails:
        lines.append(f"Guardrails: {'; '.join(str(g) for g in guardrails)}")

    prev_outputs = memory.items_with_prefix("catalog_step_output_")
    if prev_outputs:
        lines.append("")
        lines.append("Previous catalog step outputs (handoff):")
        for key in sorted(prev_outputs.keys()):
            payload = prev_outputs[key]
            summary = ""
            if isinstance(payload, dict):
                summary = str(payload.get("summary", "")).strip()
            if summary:
                lines.append(f"- {key}: {summary[:2000]}{'…' if len(summary) > 2000 else ''}")

    return "\n".join(lines)


def inject_catalog_context(
    memory_snapshot: dict[str, Any],
    *,
    agent: AgentDefinition,
    step: WorkflowStepDefinition,
    workflow: WorkflowDefinition,
) -> dict[str, Any]:
    state = dict(memory_snapshot.get("state", {}))
    events = list(memory_snapshot.get("events", []))
    state["catalog_agent"] = agent.model_dump(mode="json")
    state["catalog_step"] = step.model_dump(mode="json")
    state["catalog_workflow"] = {
        "id": workflow.id,
        "name": workflow.name,
        "goal": workflow.goal,
    }
    return {"state": state, "events": events}


def ordered_workflow_steps(workflow: WorkflowDefinition) -> list[WorkflowStepDefinition]:
    steps_by_id = {step.id: step for step in workflow.steps}
    remaining = {step.id: set(step.depends_on) for step in workflow.steps}
    ordered: list[WorkflowStepDefinition] = []

    while remaining:
        ready = [sid for sid, deps in remaining.items() if not deps]
        if not ready:
            stuck = ", ".join(sorted(remaining))
            raise ValueError(f"Workflow '{workflow.id}' has cyclic or missing dependencies: {stuck}")
        for sid in sorted(ready):
            ordered.append(steps_by_id[sid])
            del remaining[sid]
        for deps in remaining.values():
            deps.difference_update(ready)

    return ordered
