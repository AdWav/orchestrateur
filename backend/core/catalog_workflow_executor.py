from __future__ import annotations

import time

from core.agent_gateway import AgentGateway
from core.contracts import (
    AgentDefinition,
    AgentDescriptor,
    StepTiming,
    TeamSpecification,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStepDefinition,
    WorkItem,
)
from core.catalog_runtime import (
    inject_catalog_context,
    ordered_workflow_steps,
    resolve_runner_role,
)
from core.definition_catalog import DefinitionCatalog
from core.memory import SharedMemory


def workflow_to_team_specification(
    catalog: DefinitionCatalog,
    workflow_id: str,
) -> TeamSpecification:
    workflow = catalog.get_workflow(workflow_id)
    roles: list[AgentDescriptor] = []
    handoffs: list[str] = []

    ordered = ordered_workflow_steps(workflow)
    for index, step in enumerate(ordered):
        agent = catalog.get_agent(step.agent_definition_id)
        runner = resolve_runner_role(agent, step)
        roles.append(
            AgentDescriptor(
                role=runner,
                responsibility=agent.mission,
                capabilities=list(agent.capabilities),
                allowed_inputs=list(agent.inputs),
                produces=list(agent.outputs),
            )
        )
        if index > 0:
            prev = ordered[index - 1]
            prev_agent = catalog.get_agent(prev.agent_definition_id)
            handoffs.append(
                f"{prev_agent.id} -> {agent.id}: {prev.name} vers {step.name}"
            )

    return TeamSpecification(
        id=workflow.id,
        name=workflow.name,
        purpose=workflow.goal,
        methodology=workflow.context.get("methodology"),
        use_case_ids=["dev-team-benchmark"] if workflow.id.startswith("team-") else [],
        pipeline_step_ids=[resolve_runner_role(catalog.get_agent(s.agent_definition_id), s) for s in ordered],
        roles=roles,
        handoff_contracts=handoffs,
        guardrails=list(workflow.constraints),
    )


def run_catalog_workflow(
    catalog: DefinitionCatalog,
    gateway: AgentGateway,
    workflow_id: str,
    item: WorkItem,
) -> WorkflowRun:
    workflow = catalog.get_workflow(workflow_id)
    steps = ordered_workflow_steps(workflow)

    memory_state_obj = SharedMemory()
    memory_state_obj.remember("request", item.model_dump(), "system")
    memory_state_obj.remember("workflow_id", workflow_id, "system")
    memory_snapshot = memory_state_obj.snapshot()

    outputs = []
    timings: list[StepTiming] = []
    workflow_start = time.perf_counter()

    for step in steps:
        agent = catalog.get_agent(step.agent_definition_id)
        runner = resolve_runner_role(agent, step)
        memory_snapshot = inject_catalog_context(
            memory_snapshot,
            agent=agent,
            step=step,
            workflow=workflow,
        )
        step_start = time.perf_counter()
        output, memory_snapshot = gateway.run_agent(runner, item, memory_snapshot)
        duration_ms = (time.perf_counter() - step_start) * 1000.0
        timings.append(
            StepTiming(
                step_id=step.id,
                duration_ms=round(duration_ms, 2),
                approved=output.approved,
            )
        )
        outputs.append(output)

    verification_passed = bool(outputs[-1].approved) if outputs else False
    total_duration_ms = round((time.perf_counter() - workflow_start) * 1000.0, 2)

    return WorkflowRun(
        request=item,
        outputs=outputs,
        memory=memory_snapshot,
        verification_passed=verification_passed,
        team_id=workflow_id,
        step_timings=timings,
        total_duration_ms=total_duration_ms,
    )


def list_catalog_team_workflow_ids(catalog: DefinitionCatalog) -> list[str]:
    return sorted(
        definition.id
        for definition in catalog.list_workflows()
        if definition.id.startswith("team-")
    )
