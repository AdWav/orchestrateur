from __future__ import annotations

import json
from typing import Any

from core.builder.semver import AgentCompositionSnapshot, bump_agent_version
from core.builder.slug import slugify
from core.contracts import AgentDefinition, WorkflowDefinition, WorkflowStepDefinition


_COMPOSITION_SLOTS = frozenset(
    {"role", "capability", "input", "output", "guardrail", "limit", "framework"}
)


def _json_load(value: Any) -> Any:
    if isinstance(value, (str, bytes)):
        return json.loads(value)
    return value


def load_composition_rows(cursor: Any, version_id: int, *, table: str) -> list[dict[str, Any]]:
    cursor.execute(
        f"""
        SELECT slot, brick_id, sort_order, override_text
        FROM {table}
        WHERE version_id = %s
        ORDER BY slot, sort_order
        """,
        (version_id,),
    )
    return list(cursor.fetchall())


def composition_snapshot(rows: list[dict[str, Any]]) -> AgentCompositionSnapshot:
    slots: dict[str, list[int]] = {}
    for row in rows:
        slot = str(row["slot"])
        slots.setdefault(slot, []).append(int(row["brick_id"]))
    return AgentCompositionSnapshot(slots=slots)


def load_brick_labels(cursor: Any, brick_ids: list[int]) -> dict[int, str]:
    if not brick_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(brick_ids))
    cursor.execute(
        f"SELECT id, label FROM builder_bricks WHERE id IN ({placeholders})",
        brick_ids,
    )
    return {int(row["id"]): str(row["label"]) for row in cursor.fetchall()}


def runtime_id_for_custom_agent(slug: str) -> str:
    base = slugify(slug)[:48]
    return f"custom-{base}"


def runtime_id_for_custom_workflow(slug: str) -> str:
    base = slugify(slug)[:48]
    return f"custom-wf-{base}"


def materialize_custom_agent_definition(
    cursor: Any,
    *,
    version_id: int,
    slug: str,
    payload: dict[str, Any],
) -> AgentDefinition:
    runtime_id = runtime_id_for_custom_agent(slug)
    merged = {**payload, "id": runtime_id}
    return materialize_agent_definition(
        cursor,
        version_id=version_id,
        payload=merged,
        composition_table="builder_custom_agent_composition",
    )


def materialize_custom_workflow_definition(
    cursor: Any,
    *,
    version_id: int,
    slug: str,
    payload: dict[str, Any],
) -> WorkflowDefinition:
    runtime_id = runtime_id_for_custom_workflow(slug)
    merged = {**payload, "id": runtime_id}
    cursor.execute(
        """
        SELECT step_id, name, objective, agent_definition_id,
               depends_on_merged, sort_order, runner_role_override
        FROM builder_custom_workflow_steps
        WHERE version_id = %s
        ORDER BY sort_order
        """,
        (version_id,),
    )
    steps: list[WorkflowStepDefinition] = []
    for row in cursor.fetchall():
        depends = _json_load(row["depends_on_merged"]) or []
        steps.append(
            WorkflowStepDefinition(
                id=str(row["step_id"]),
                name=str(row["name"]),
                agent_definition_id=str(row["agent_definition_id"]),
                objective=str(row["objective"]),
                runner_role=row.get("runner_role_override"),
                depends_on=[str(value) for value in depends],
            )
        )
    if steps:
        return WorkflowDefinition(
            id=runtime_id,
            name=str(merged["name"]),
            goal=str(merged["goal"]),
            context={str(k): str(v) for k, v in (merged.get("context") or {}).items()},
            constraints=[str(value) for value in merged.get("constraints") or []],
            success_criteria=[str(value) for value in merged.get("success_criteria") or []],
            steps=steps,
        )
    return WorkflowDefinition.model_validate(merged)


def materialize_agent_definition(
    cursor: Any,
    *,
    version_id: int,
    payload: dict[str, Any],
    composition_table: str = "builder_agent_composition",
) -> AgentDefinition:
    rows = load_composition_rows(cursor, version_id, table=composition_table)
    labels = load_brick_labels(cursor, [int(row["brick_id"]) for row in rows])

    by_slot: dict[str, list[str]] = {slot: [] for slot in _COMPOSITION_SLOTS}
    for row in rows:
        slot = str(row["slot"])
        text = row.get("override_text") or labels.get(int(row["brick_id"]), "")
        if text and slot in by_slot:
            by_slot[slot].append(str(text).strip())

    runner = payload.get("runner_role") or ""
    return AgentDefinition(
        id=str(payload["id"]),
        name=str(payload.get("name") or payload["id"]),
        business_role=str(payload.get("business_role") or by_slot["role"][0] if by_slot["role"] else ""),
        mission=str(payload.get("mission") or ""),
        runner_role=str(runner) if runner else "",
        capabilities=by_slot["capability"] or list(payload.get("capabilities") or []),
        inputs=by_slot["input"] or list(payload.get("inputs") or []),
        outputs=by_slot["output"] or list(payload.get("outputs") or []),
        guardrails=by_slot["guardrail"] or list(payload.get("guardrails") or []),
    )


def materialize_workflow_definition(
    cursor: Any,
    *,
    version_id: int,
    payload: dict[str, Any],
) -> WorkflowDefinition:
    cursor.execute(
        """
        SELECT step_id, name, objective, agent_definition_id, runner_role_override,
               depends_on_merged, sort_order
        FROM builder_workflow_steps
        WHERE version_id = %s
        ORDER BY sort_order
        """,
        (version_id,),
    )
    steps: list[WorkflowStepDefinition] = []
    for row in cursor.fetchall():
        depends = _json_load(row["depends_on_merged"]) or []
        steps.append(
            WorkflowStepDefinition(
                id=str(row["step_id"]),
                name=str(row["name"]),
                agent_definition_id=str(row["agent_definition_id"]),
                objective=str(row["objective"]),
                runner_role=row.get("runner_role_override"),
                depends_on=[str(value) for value in depends],
            )
        )
    if steps:
        return WorkflowDefinition(
            id=str(payload["id"]),
            name=str(payload["name"]),
            goal=str(payload["goal"]),
            context={str(k): str(v) for k, v in (payload.get("context") or {}).items()},
            constraints=[str(value) for value in payload.get("constraints") or []],
            success_criteria=[str(value) for value in payload.get("success_criteria") or []],
            steps=steps,
        )
    return WorkflowDefinition.model_validate(payload)


def upsert_runtime_agent(cursor: Any, definition: AgentDefinition) -> None:
    payload = definition.model_dump(mode="json")
    cursor.execute(
        """
        INSERT INTO agent_definitions (id, payload)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE payload = VALUES(payload), updated_at = CURRENT_TIMESTAMP
        """,
        (definition.id, json.dumps(payload)),
    )


def upsert_runtime_workflow(cursor: Any, definition: WorkflowDefinition) -> None:
    payload = definition.model_dump(mode="json")
    cursor.execute(
        """
        INSERT INTO workflow_definitions (id, payload)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE payload = VALUES(payload), updated_at = CURRENT_TIMESTAMP
        """,
        (definition.id, json.dumps(payload)),
    )


def next_agent_version(
    cursor: Any,
    agent_id: str,
    *,
    current_rows: list[dict[str, Any]],
    mission_scope_changed: bool = False,
    cosmetic_only: bool = False,
) -> str:
    cursor.execute(
        """
        SELECT version, id, status FROM builder_agent_versions
        WHERE agent_id = %s
        ORDER BY created_at DESC LIMIT 1
        """,
        (agent_id,),
    )
    latest = cursor.fetchone()
    if latest is None:
        return "1.0.0"

    base_version = str(latest["version"])
    if latest["status"] == "draft":
        parts = base_version.split(".")
        return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"

    prev_rows = load_composition_rows(cursor, int(latest["id"]))
    return bump_agent_version(
        base_version,
        previous=composition_snapshot(prev_rows),
        current_composition=composition_snapshot(current_rows),
        runner_role_changed=False,
        mission_scope_changed=mission_scope_changed,
        cosmetic_only=cosmetic_only,
    )
