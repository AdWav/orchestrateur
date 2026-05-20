from __future__ import annotations

import json
from typing import Any


def _json_load(value: Any) -> Any:
    if isinstance(value, (str, bytes)):
        return json.loads(value)
    return value


_AGENT_PAYLOAD_FIELDS = frozenset(
    {"name", "business_role", "mission", "runner_role", "capabilities", "inputs", "outputs", "guardrails"}
)


def apply_agent_field_update(
    cursor: Any,
    *,
    version_id: int,
    field_path: str,
    proposed_value: Any,
) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT id, agent_id, status, payload, runner_role
        FROM builder_agent_versions WHERE id = %s
        """,
        (version_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"Unknown agent version '{version_id}'.")
    if row["status"] != "draft":
        raise ValueError(f"Version '{version_id}' is not a draft.")

    payload = _json_load(row["payload"]) or {}
    before = {
        "payload": dict(payload),
        "runner_role": row.get("runner_role"),
    }
    field = field_path.strip()

    if field in _AGENT_PAYLOAD_FIELDS:
        if field == "runner_role":
            runner = str(proposed_value) if proposed_value else None
            payload["runner_role"] = runner or ""
            cursor.execute(
                """
                UPDATE builder_agent_versions
                SET runner_role = %s, payload = %s
                WHERE id = %s
                """,
                (runner, json.dumps(payload), version_id),
            )
        else:
            payload[field] = proposed_value
            cursor.execute(
                "UPDATE builder_agent_versions SET payload = %s WHERE id = %s",
                (json.dumps(payload), version_id),
            )
    elif field.startswith("payload."):
        key = field[len("payload.") :]
        nested = dict(payload)
        nested[key] = proposed_value
        cursor.execute(
            "UPDATE builder_agent_versions SET payload = %s WHERE id = %s",
            (json.dumps(nested), version_id),
        )
        payload = nested
    else:
        raise ValueError(f"Unsupported agent field_path: {field_path!r}")

    return {
        "version_id": version_id,
        "agent_id": row["agent_id"],
        "before": before,
        "after": {"payload": payload, "runner_role": payload.get("runner_role")},
    }
