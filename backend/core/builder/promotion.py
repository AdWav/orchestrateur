from __future__ import annotations

import json
from typing import Any

from core.builder.compose import load_brick_labels, load_composition_rows, next_agent_version, upsert_runtime_agent
from core.contracts import AgentDefinition


def promote_custom_agent_to_catalog(
    cursor: Any,
    *,
    custom_agent_id: str,
    catalog_agent_id: str,
    domain_id: int | None,
    published_by: str,
) -> dict[str, Any]:
    cursor.execute(
        "SELECT id, slug FROM builder_custom_agents WHERE id = %s",
        (custom_agent_id,),
    )
    custom_row = cursor.fetchone()
    if custom_row is None:
        raise KeyError(f"Unknown custom agent '{custom_agent_id}'.")

    cursor.execute(
        """
        SELECT id, version, payload, runner_role
        FROM builder_custom_agent_versions
        WHERE custom_agent_id = %s AND status = 'published'
        ORDER BY created_at DESC LIMIT 1
        """,
        (custom_agent_id,),
    )
    custom_version = cursor.fetchone()
    if custom_version is None:
        raise ValueError("Custom agent has no published version to promote.")

    payload = custom_version["payload"]
    if isinstance(payload, (str, bytes)):
        payload = json.loads(payload)

    catalog_payload = {
        "id": catalog_agent_id,
        "name": str(payload.get("name") or custom_row["slug"]),
        "business_role": str(payload.get("business_role") or payload.get("name") or ""),
        "mission": str(payload.get("mission") or ""),
        "runner_role": payload.get("runner_role") or "",
    }

    comp_rows = load_composition_rows(
        cursor,
        int(custom_version["id"]),
        table="builder_custom_agent_composition",
    )
    comp_for_version = [
        {"slot": row["slot"], "brick_id": int(row["brick_id"]), "sort_order": int(row["sort_order"])}
        for row in comp_rows
    ]

    cursor.execute(
        """
        INSERT INTO builder_agents (id, domain_id) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE domain_id = VALUES(domain_id)
        """,
        (catalog_agent_id, domain_id),
    )

    version_str = next_agent_version(cursor, catalog_agent_id, current_rows=comp_for_version)
    labels = load_brick_labels(cursor, [int(r["brick_id"]) for r in comp_rows])
    by_slot: dict[str, list[str]] = {}
    for row in comp_rows:
        slot = str(row["slot"])
        text = labels.get(int(row["brick_id"]), "")
        if text:
            by_slot.setdefault(slot, []).append(text)

    runner = catalog_payload.get("runner_role") or ""
    definition = AgentDefinition(
        id=catalog_agent_id,
        name=catalog_payload["name"],
        business_role=catalog_payload["business_role"] or (by_slot.get("role") or [""])[0],
        mission=catalog_payload["mission"],
        runner_role=str(runner) if runner else "",
        capabilities=by_slot.get("capability") or [],
        inputs=by_slot.get("input") or [],
        outputs=by_slot.get("output") or [],
        guardrails=by_slot.get("guardrail") or [],
    )
    AgentDefinition.model_validate(definition.model_dump())

    cursor.execute(
        """
        INSERT INTO builder_agent_versions (
            agent_id, version, status, payload, runner_role, published_at, published_by, created_by
        ) VALUES (%s, %s, 'published', %s, %s, CURRENT_TIMESTAMP, %s, %s)
        """,
        (
            catalog_agent_id,
            version_str,
            json.dumps(definition.model_dump(mode="json")),
            custom_version.get("runner_role"),
            published_by,
            published_by,
        ),
    )
    catalog_version_id = int(cursor.lastrowid)

    for item in comp_for_version:
        cursor.execute(
            """
            INSERT INTO builder_agent_composition (version_id, brick_id, slot, sort_order)
            VALUES (%s, %s, %s, %s)
            """,
            (
                catalog_version_id,
                item["brick_id"],
                item["slot"],
                item["sort_order"],
            ),
        )

    cursor.execute(
        """
        UPDATE builder_agent_versions SET status = 'archived'
        WHERE agent_id = %s AND status = 'published' AND id != %s
        """,
        (catalog_agent_id, catalog_version_id),
    )
    cursor.execute(
        "UPDATE builder_agents SET published_version_id = %s WHERE id = %s",
        (catalog_version_id, catalog_agent_id),
    )
    cursor.execute(
        """
        UPDATE builder_custom_agent_versions
        SET promotion_status = 'promoted'
        WHERE id = %s
        """,
        (custom_version["id"],),
    )
    upsert_runtime_agent(cursor, definition)

    return {
        "catalog_agent_id": catalog_agent_id,
        "catalog_version_id": catalog_version_id,
        "version": version_str,
    }
