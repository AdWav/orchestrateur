from __future__ import annotations

import pytest

from core.builder.semver import (
    AgentCompositionSnapshot,
    VersionBump,
    VersionTriple,
    bump_agent_version,
    parse_version,
)


def test_parse_version() -> None:
    assert str(parse_version("1.0.0")) == "1.0.0"


def test_version_bump() -> None:
    base = parse_version("2.3.4")
    assert str(base.bump(VersionBump.PATCH)) == "2.3.5"
    assert str(base.bump(VersionBump.MINOR)) == "2.4.0"
    assert str(base.bump(VersionBump.MAJOR)) == "3.0.0"


def test_bump_agent_patch_cosmetic() -> None:
    comp = AgentCompositionSnapshot(slots={"capability": [1, 2]})
    result = bump_agent_version(
        "1.0.0",
        previous=comp,
        current_composition=comp,
        runner_role_changed=False,
        mission_scope_changed=False,
        cosmetic_only=True,
    )
    assert result == "1.0.1"


def test_bump_agent_major_runner_change() -> None:
    comp = AgentCompositionSnapshot(slots={"role": [1]})
    result = bump_agent_version(
        "1.0.0",
        previous=comp,
        current_composition=comp,
        runner_role_changed=True,
        mission_scope_changed=False,
    )
    assert result == "2.0.0"


def test_bump_agent_minor_add_brick() -> None:
    prev = AgentCompositionSnapshot(slots={"capability": [1]})
    curr = AgentCompositionSnapshot(slots={"capability": [1, 2]})
    result = bump_agent_version(
        "1.0.0",
        previous=prev,
        current_composition=curr,
        runner_role_changed=False,
        mission_scope_changed=False,
    )
    assert result == "1.1.0"


def test_parse_version_invalid() -> None:
    with pytest.raises(ValueError):
        parse_version("v1")
