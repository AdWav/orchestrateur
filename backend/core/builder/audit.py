from __future__ import annotations

import json
from typing import Any

from core.builder.connection import connect


def log_audit_event(
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_type: str,
    actor_id: str,
    entity_version: str | None = None,
    before_payload: dict[str, Any] | None = None,
    after_payload: dict[str, Any] | None = None,
    session_id: str | None = None,
    correlation_id: str | None = None,
) -> int:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO builder_audit_events (
                    session_id, entity_type, entity_id, entity_version,
                    action, actor_type, actor_id,
                    before_payload, after_payload, correlation_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    entity_type,
                    entity_id,
                    entity_version,
                    action,
                    actor_type,
                    actor_id,
                    json.dumps(before_payload) if before_payload is not None else None,
                    json.dumps(after_payload) if after_payload is not None else None,
                    correlation_id,
                ),
            )
            event_id = int(cursor.lastrowid)
        conn.commit()
    return event_id
