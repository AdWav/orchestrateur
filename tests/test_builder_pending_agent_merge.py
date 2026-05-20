from __future__ import annotations

import pytest

from core.builder.pending_agent_merge import apply_agent_field_update


class _FakeCursor:
    def __init__(self, row: dict, payload: dict) -> None:
        self._row = row
        self._payload = payload
        self.updates: list[tuple] = []

    def execute(self, sql: str, params: tuple | None = None) -> None:
        if "SELECT id, agent_id" in sql:
            self._row["payload"] = self._payload
        elif "UPDATE builder_agent_versions" in sql:
            self.updates.append((sql, params))

    def fetchone(self) -> dict:
        return self._row


def test_apply_agent_field_mission() -> None:
    payload = {"id": "test", "name": "T", "business_role": "R", "mission": "old"}
    row = {"id": 1, "agent_id": "test", "status": "draft", "payload": payload, "runner_role": None}
    cursor = _FakeCursor(row, payload)
    result = apply_agent_field_update(
        cursor,
        version_id=1,
        field_path="mission",
        proposed_value="new mission",
    )
    assert result["after"]["payload"]["mission"] == "new mission"
    assert cursor.updates
