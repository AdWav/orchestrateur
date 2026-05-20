from __future__ import annotations

from core.builder.compose import AgentCompositionSnapshot, composition_snapshot
from core.builder.semver import bump_agent_version


def test_composition_snapshot_groups_bricks() -> None:
    rows = [
        {"slot": "capability", "brick_id": 10, "sort_order": 0},
        {"slot": "capability", "brick_id": 20, "sort_order": 1},
        {"slot": "role", "brick_id": 5, "sort_order": 0},
    ]
    snapshot = composition_snapshot(rows)
    assert snapshot.slots["capability"] == [10, 20]
    assert snapshot.slots["role"] == [5]


def test_bump_from_composition_minor() -> None:
    prev = AgentCompositionSnapshot(slots={"role": [1], "capability": [2]})
    curr = AgentCompositionSnapshot(slots={"role": [1], "capability": [2, 3]})
    result = bump_agent_version(
        "1.0.0",
        previous=prev,
        current_composition=curr,
        runner_role_changed=False,
        mission_scope_changed=False,
    )
    assert result == "1.1.0"
